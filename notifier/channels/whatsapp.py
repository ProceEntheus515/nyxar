"""
Canal WhatsApp: API Cloud (Meta) o gateway HTTP. Async con httpx.
Sin Twilio. Sin adjuntos. Texto corto y sin datos técnicos en el cuerpo.
"""

from __future__ import annotations

import asyncio
import hashlib
import os
import re
import time
from typing import Any, Callable, Optional

import httpx

from notifier.models import NotifMessage, Recipient
from shared.logger import get_logger

logger = get_logger("notifier.whatsapp")

_RE_IP = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
_RE_CVE = re.compile(r"\bCVE-\d{4}-\d+\b", re.I)
_RE_PORT = re.compile(r"\b(?:puerto|port)\s*:?\s*\d{2,5}\b", re.I)


def _mask_dest_id(raw: str) -> str:
    d = "".join(c for c in (raw or "") if c.isdigit())
    if len(d) < 4:
        return "***"
    return f"***{d[-4:]}"


def _dest_rate_key(raw: str) -> str:
    norm = "".join(c for c in (raw or "") if c.isdigit())
    h = hashlib.sha256(norm.encode("utf-8")).hexdigest()[:16]
    return f"notif:wa:1m:{h}"


class WhatsAppChannel:
    """
    WhatsApp Business Cloud (Meta) o NOTIFY_WHATSAPP_HTTP_URL.
    Máximo 1 envío por minuto por destino (Redis); sin loguear número completo.
    """

    def __init__(self, redis_client_getter: Optional[Callable[[], Any]] = None) -> None:
        self._redis_getter = redis_client_getter

    @staticmethod
    def _truncate_for_whatsapp(texto: str, max_len: int = 200) -> str:
        t = _RE_IP.sub("[redacted]", texto or "")
        t = _RE_CVE.sub("[CVE]", t)
        t = _RE_PORT.sub("[puerto]", t)
        t = " ".join(t.split())
        if len(t) > max_len:
            return t[: max_len - 3] + "..."
        return t

    def _format_line(self, mensaje: NotifMessage) -> str:
        core = self._truncate_for_whatsapp(
            mensaje.cuerpo_corto or mensaje.titulo or "Alerta NYXAR",
            max_len=120,
        )
        link = (mensaje.link or "").strip()
        if len(link) > 50:
            link = "dashboard"
        elif not link:
            link = "dashboard"
        line = f"ALERTA {mensaje.severidad} | {core} | Ver: {link}"
        return line[:200]

    async def _rate_allow(self, dest_raw: str) -> bool:
        getter = self._redis_getter
        if not getter:
            return True
        client = getter()
        if not client:
            return True
        key = _dest_rate_key(dest_raw)
        try:
            n = await client.incr(key)
            if n == 1:
                await client.expire(key, 60)
            if n > 1:
                logger.warning("WhatsApp: rate 1/min por destino, omitido dest=%s", _mask_dest_id(dest_raw))
                return False
        except Exception as e:
            logger.warning("WhatsApp rate redis: %s", e)
            return True
        return True

    async def _post_meta(self, to_digits: str, body: str) -> bool:
        token = os.getenv("WHATSAPP_CLOUD_ACCESS_TOKEN", "").strip()
        phone_id = os.getenv("WHATSAPP_CLOUD_PHONE_NUMBER_ID", "").strip()
        version = (os.getenv("WHATSAPP_CLOUD_API_VERSION", "v21.0") or "v21.0").strip()
        if not token or not phone_id:
            return False
        url = f"https://graph.facebook.com/{version}/{phone_id}/messages"
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to_digits,
            "type": "text",
            "text": {"preview_url": False, "body": body[:4096]},
        }
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                r = await client.post(
                    url,
                    json=payload,
                    headers={"Authorization": f"Bearer {token}"},
                )
            if r.status_code >= 400:
                logger.error("WhatsApp Cloud HTTP %s", r.status_code)
                return False
            return True
        except Exception as e:
            logger.error("WhatsApp Cloud fallo: %s", e)
            return False

    async def _post_gateway(self, to_e164: str, body: str) -> bool:
        base = os.getenv("NOTIFY_WHATSAPP_HTTP_URL", "").strip()
        if not base:
            return False
        bearer = os.getenv("NOTIFY_WHATSAPP_HTTP_BEARER", "").strip()
        to_key = (os.getenv("NOTIFY_WHATSAPP_HTTP_KEY_TO", "to") or "to").strip()
        msg_key = (os.getenv("NOTIFY_WHATSAPP_HTTP_KEY_MESSAGE", "message") or "message").strip()
        to_val = to_e164 if to_e164.startswith("+") else f"+{to_e164}"
        payload = {to_key: to_val, msg_key: body[:4096]}
        headers = {"Content-Type": "application/json"}
        if bearer:
            headers["Authorization"] = f"Bearer {bearer}"
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                r = await client.post(base, json=payload, headers=headers)
            if r.status_code >= 400:
                logger.error("WhatsApp gateway HTTP %s", r.status_code)
                return False
            return True
        except Exception as e:
            logger.error("WhatsApp gateway fallo: %s", e)
            return False

    async def _send_once(self, to_e164: str, body: str) -> bool:
        digits = "".join(c for c in to_e164 if c.isdigit())
        if len(digits) < 10:
            return False

        has_cloud = bool(
            os.getenv("WHATSAPP_CLOUD_ACCESS_TOKEN", "").strip()
            and os.getenv("WHATSAPP_CLOUD_PHONE_NUMBER_ID", "").strip()
        )
        has_http = bool(os.getenv("NOTIFY_WHATSAPP_HTTP_URL", "").strip())

        if has_cloud:
            if await self._post_meta(digits, body):
                return True
            if not has_http:
                return False

        if has_http:
            return await self._post_gateway(to_e164, body)

        logger.info("WhatsApp (sin API): dest=%s", _mask_dest_id(to_e164))
        return True

    async def send(self, recipient: Recipient, mensaje: NotifMessage) -> bool:
        if not recipient.whatsapp_number:
            return False
        if not await self._rate_allow(recipient.whatsapp_number):
            return False

        line = self._format_line(mensaje)

        async def once() -> bool:
            return await self._send_once(recipient.whatsapp_number, line)

        t0 = time.monotonic()
        ok = await once()
        if not ok:
            await asyncio.sleep(5)
            ok = await once()
        lat = int((time.monotonic() - t0) * 1000)
        logger.info(
            "canal=whatsapp tipo=%s dest=%s ok=%s lat_ms=%s",
            mensaje.tipo,
            _mask_dest_id(recipient.whatsapp_number),
            ok,
            lat,
        )
        return ok


async def send_whatsapp_plain(to_e164: str, body_plain: str) -> bool:
    msg = NotifMessage(
        tipo="alerta",
        severidad="ALTA",
        titulo="NYXAR",
        cuerpo=body_plain,
        cuerpo_corto=body_plain[:200],
    )
    r = Recipient(id="legacy", nombre="", whatsapp_number=to_e164)
    ch = WhatsAppChannel()
    return await ch.send(r, msg)
