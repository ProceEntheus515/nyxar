"""
Carga de destinatarios desde variables de entorno (emails y WhatsApp, sin Slack).
"""

from __future__ import annotations

import os
import re
import uuid
from typing import List

from notifier.models import NotifPreferences, Recipient

_WS = re.compile(r"[\s,;]+")


def _split_csv(raw: str | None) -> list[str]:
    if not raw or not str(raw).strip():
        return []
    return [p.strip() for p in _WS.split(str(raw).strip()) if p.strip()]


def _is_email(s: str) -> bool:
    return "@" in s and not s.startswith("+")


def _is_phone(s: str) -> bool:
    return s.startswith("+") and len(s) >= 10


def load_recipients_from_env() -> list[Recipient]:
    """
    Variables soportadas (CSV):
    - NOTIFY_ADMIN_EMAILS, NOTIFY_ADMIN_WHATSAPP
    - NOTIFY_SECURITY_EMAILS, NOTIFY_SECURITY_WHATSAPP
    - NOTIFY_REPORT_EMAILS, NOTIFY_REPORT_WHATSAPP
    """
    out: list[Recipient] = []

    def add_pair(emails_key: str, wa_key: str, es_admin: bool, prefix: str) -> None:
        emails = _split_csv(os.getenv(emails_key, ""))
        phones = _split_csv(os.getenv(wa_key, ""))
        for i, em in enumerate(emails):
            if not _is_email(em):
                continue
            rid = f"{prefix}-email-{i}-{uuid.uuid4().hex[:6]}"
            out.append(
                Recipient(
                    id=rid,
                    nombre=prefix,
                    email=em,
                    es_admin=es_admin,
                    preferencias=NotifPreferences(email_enabled=True, whatsapp_enabled=False),
                )
            )
        for i, ph in enumerate(phones):
            if not _is_phone(ph):
                continue
            rid = f"{prefix}-wa-{i}-{uuid.uuid4().hex[:6]}"
            out.append(
                Recipient(
                    id=rid,
                    nombre=f"{prefix} (WhatsApp)",
                    whatsapp_number=ph,
                    es_admin=es_admin,
                    preferencias=NotifPreferences(email_enabled=False, whatsapp_enabled=True),
                )
            )

    add_pair("NOTIFY_ADMIN_EMAILS", "NOTIFY_ADMIN_WHATSAPP", True, "admin")
    add_pair("NOTIFY_SECURITY_EMAILS", "NOTIFY_SECURITY_WHATSAPP", False, "security")
    add_pair("NOTIFY_REPORT_EMAILS", "NOTIFY_REPORT_WHATSAPP", False, "report")

    return out
