import os
import smtplib
from email.mime.text import MIMEText

from shared.logger import get_logger

logger = get_logger("notifier.email")


def send_email(to_addr: str, subject: str, body_text: str) -> bool:
    """
    Envía correo vía SMTP si NOTIFY_SMTP_HOST está definido; si no, solo registra en log.
    """
    host = os.getenv("NOTIFY_SMTP_HOST", "").strip()
    if not host:
        logger.info("Email (sin SMTP): to=%s subject=%s", to_addr, subject[:80])
        return True

    port = int(os.getenv("NOTIFY_SMTP_PORT", "587") or "587")
    user = os.getenv("NOTIFY_SMTP_USER", "").strip()
    password = os.getenv("NOTIFY_SMTP_PASSWORD", "").strip()
    from_addr = os.getenv("NOTIFY_SMTP_FROM", user or "nyxar@localhost")

    msg = MIMEText(body_text, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = to_addr

    try:
        with smtplib.SMTP(host, port, timeout=30) as smtp:
            smtp.ehlo()
            if os.getenv("NOTIFY_SMTP_TLS", "true").lower() in ("1", "true", "yes"):
                smtp.starttls()
            if user and password:
                smtp.login(user, password)
            smtp.sendmail(from_addr, [to_addr], msg.as_string())
        return True
    except Exception as e:
        logger.error("send_email fallo: %s", e)
        return False
