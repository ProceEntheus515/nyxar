import json
import os
import urllib.error
import urllib.request

from shared.logger import get_logger

logger = get_logger("notifier.whatsapp")

# Texto genérico: sin IPs, CVEs ni datos técnicos en WA (regla NYXAR).
DEFAULT_WA_BODY = "Alerta en NYXAR. Ingresá al dashboard de seguridad para más detalle."


def _digits_e164(to_e164: str) -> str:
    """Meta Cloud API usa el número en dígitos, sin '+' ni espacios."""
    return "".join(c for c in (to_e164 or "") if c.isdigit())


def _send_meta_cloud(to_digits: str, body: str) -> bool:
    token = os.getenv("WHATSAPP_CLOUD_ACCESS_TOKEN", "").strip()
    phone_id = os.getenv("WHATSAPP_CLOUD_PHONE_NUMBER_ID", "").strip()
    version = os.getenv("WHATSAPP_CLOUD_API_VERSION", "v21.0").strip() or "v21.0"

    if not token or not phone_id:
        return False

    url = f"https://graph.facebook.com/{version}/{phone_id}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to_digits,
        "type": "text",
        "text": {"preview_url": False, "body": body},
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", "application/json")

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            if resp.status >= 400:
                logger.error("WhatsApp Cloud API HTTP %s", resp.status)
                return False
        return True
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")[:500]
        logger.error("WhatsApp Cloud API error %s: %s", e.code, err_body)
        return False
    except Exception as e:
        logger.error("WhatsApp Cloud API fallo: %s", e)
        return False


def _send_http_gateway(to_e164: str, body: str) -> bool:
    """
    Gateway propio u otro proveedor: POST JSON a NOTIFY_WHATSAPP_HTTP_URL.
    Cuerpo: {"to": "+549...", "message": "..."} (ajustable con NOTIFY_WHATSAPP_HTTP_BODY_KEYS).
    """
    base = os.getenv("NOTIFY_WHATSAPP_HTTP_URL", "").strip()
    if not base:
        return False

    bearer = os.getenv("NOTIFY_WHATSAPP_HTTP_BEARER", "").strip()
    to_key = os.getenv("NOTIFY_WHATSAPP_HTTP_KEY_TO", "to").strip() or "to"
    msg_key = os.getenv("NOTIFY_WHATSAPP_HTTP_KEY_MESSAGE", "message").strip() or "message"

    payload = {to_key: to_e164 if to_e164.startswith("+") else f"+{to_e164}", msg_key: body}
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(base, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    if bearer:
        req.add_header("Authorization", f"Bearer {bearer}")

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            if resp.status >= 400:
                logger.error("WhatsApp HTTP gateway HTTP %s", resp.status)
                return False
        return True
    except urllib.error.HTTPError as e:
        logger.error("WhatsApp HTTP gateway error %s", e.code)
        return False
    except Exception as e:
        logger.error("WhatsApp HTTP gateway fallo: %s", e)
        return False


def send_whatsapp_plain(to_e164: str, body_plain: str) -> bool:
    """
    Envío vía API oficial WhatsApp Cloud (Meta) o, si no está configurada,
    vía NOTIFY_WHATSAPP_HTTP_URL (gateway interno).

    Sin credenciales: solo log (degradación elegante).
    """
    safe = (body_plain or "").strip() or DEFAULT_WA_BODY
    if len(safe) > 4096:
        safe = safe[:4093] + "..."

    to_digits = _digits_e164(to_e164)
    if not to_digits or len(to_digits) < 10:
        logger.warning("WhatsApp: número inválido %r", to_e164)
        return False

    has_cloud = bool(
        os.getenv("WHATSAPP_CLOUD_ACCESS_TOKEN", "").strip()
        and os.getenv("WHATSAPP_CLOUD_PHONE_NUMBER_ID", "").strip()
    )
    has_http = bool(os.getenv("NOTIFY_WHATSAPP_HTTP_URL", "").strip())

    if has_cloud:
        if _send_meta_cloud(to_digits, safe):
            return True
        if not has_http:
            logger.error("WhatsApp Cloud API falló y no hay NOTIFY_WHATSAPP_HTTP_URL")
            return False
        logger.warning("WhatsApp Cloud falló; reintentando vía gateway HTTP")

    if has_http:
        return _send_http_gateway(to_e164, safe)

    logger.info("WhatsApp (sin API configurada): to=%s msg=%s", to_e164, safe[:120])
    return True
