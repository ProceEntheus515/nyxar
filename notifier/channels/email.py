"""
Canal email async (aiosmtplib) con plantillas Jinja2 en tablas HTML.
"""

from __future__ import annotations

import asyncio
import os
import time
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

import aiosmtplib
from jinja2 import Environment, FileSystemLoader, select_autoescape

from notifier.models import NotifMessage, Recipient
from shared.logger import get_logger

logger = get_logger("notifier.email")

_MAX_ATTACH = 10 * 1024 * 1024
_TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates" / "email"


def _smtp_config() -> dict:
    host = (os.getenv("NOTIFY_SMTP_HOST") or os.getenv("SMTP_HOST") or "").strip()
    port = int(os.getenv("NOTIFY_SMTP_PORT") or os.getenv("SMTP_PORT") or "587")
    user = (os.getenv("NOTIFY_SMTP_USER") or os.getenv("SMTP_USER") or "").strip()
    password = (os.getenv("NOTIFY_SMTP_PASSWORD") or os.getenv("SMTP_PASSWORD") or "").strip()
    from_addr = (
        os.getenv("NOTIFY_SMTP_FROM")
        or os.getenv("EMAIL_FROM")
        or user
        or "nyxar@localhost"
    ).strip()
    use_tls = (os.getenv("NOTIFY_SMTP_TLS") or os.getenv("SMTP_USE_TLS", "true")).lower() in (
        "1",
        "true",
        "yes",
    )
    return {
        "host": host,
        "port": port,
        "user": user,
        "password": password,
        "from_addr": from_addr,
        "use_tls": use_tls,
    }


class EmailChannel:
    """Envía HTML multiparte (tablas) + texto plano; adjuntos PDF hasta 10MB."""

    def __init__(self) -> None:
        self._jinja = Environment(
            loader=FileSystemLoader(str(_TEMPLATES_DIR)),
            autoescape=select_autoescape(["html", "xml"]),
        )

    def _template_name(self, mensaje: NotifMessage) -> str:
        if mensaje.tipo == "reporte":
            return "reporte.html"
        if mensaje.tipo == "aprobacion":
            return "aprobacion.html"
        return "alerta.html"

    def _build_html(self, mensaje: NotifMessage) -> str:
        import html as html_mod

        cuerpo_html = html_mod.escape(mensaje.cuerpo or "").replace("\n", "<br />\n")
        tpl = self._jinja.get_template(self._template_name(mensaje))
        return tpl.render(
            titulo=mensaje.titulo,
            severidad=mensaje.severidad,
            cuerpo_html=cuerpo_html,
            link=mensaje.link or "",
        )

    def _build_plain(self, mensaje: NotifMessage) -> str:
        parts = [mensaje.titulo, "", mensaje.cuerpo or ""]
        if mensaje.link:
            parts.extend(["", f"Ver en dashboard: {mensaje.link}"])
        parts.append("")
        parts.append("Este email fue generado automáticamente por NYXAR.")
        return "\n".join(parts)

    async def _send_once(self, to_addr: str, mensaje: NotifMessage) -> bool:
        cfg = _smtp_config()
        if not cfg["host"]:
            logger.info("Email (sin SMTP): subject=%s", (mensaje.titulo or "")[:80])
            return True

        html_body = self._build_html(mensaje)
        plain_body = self._build_plain(mensaje)

        if mensaje.attachment_path and Path(mensaje.attachment_path).is_file():
            p = Path(mensaje.attachment_path)
            size = p.stat().st_size
            if size > _MAX_ATTACH:
                logger.error("Adjunto supera 10MB: %s", p.name)
                return False
            msg = MIMEMultipart("mixed")
            alt = MIMEMultipart("alternative")
            alt.attach(MIMEText(plain_body, "plain", "utf-8"))
            alt.attach(MIMEText(html_body, "html", "utf-8"))
            msg.attach(alt)
            with open(p, "rb") as f:
                part = MIMEApplication(f.read(), _subtype="pdf")
            part.add_header("Content-Disposition", "attachment", filename=p.name)
            msg.attach(part)
        else:
            msg = MIMEMultipart("alternative")
            msg.attach(MIMEText(plain_body, "plain", "utf-8"))
            msg.attach(MIMEText(html_body, "html", "utf-8"))

        msg["Subject"] = mensaje.titulo[:200]
        msg["From"] = cfg["from_addr"]
        msg["To"] = to_addr

        try:
            client = aiosmtplib.SMTP(
                hostname=cfg["host"],
                port=cfg["port"],
                timeout=30,
            )
            await client.connect()
            if cfg["use_tls"]:
                await client.starttls()
            if cfg["user"] and cfg["password"]:
                await client.login(cfg["user"], cfg["password"])
            await client.send_message(msg)
            await client.quit()
            return True
        except Exception as e:
            logger.error("SMTP fallo: %s", e)
            return False

    async def send(self, recipient: Recipient, mensaje: NotifMessage) -> bool:
        if not recipient.email:
            return False

        async def once() -> bool:
            return await self._send_once(recipient.email, mensaje)

        t0 = time.monotonic()
        ok = await once()
        if not ok:
            await asyncio.sleep(5)
            ok = await once()
        lat = int((time.monotonic() - t0) * 1000)
        logger.info(
            "canal=email tipo=%s dest=*** ok=%s lat_ms=%s",
            mensaje.tipo,
            ok,
            lat,
        )
        return ok


async def send_email(to_addr: str, subject: str, body_text: str) -> bool:
    """Compatibilidad con llamadas antiguas (solo texto)."""
    msg = NotifMessage(
        tipo="alerta",
        severidad="media",
        titulo=subject,
        cuerpo=body_text,
        cuerpo_corto=body_text[:200],
    )
    r = Recipient(id="legacy", nombre="", email=to_addr)
    ch = EmailChannel()
    return await ch.send(r, msg)
