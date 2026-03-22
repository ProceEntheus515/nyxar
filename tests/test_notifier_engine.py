"""Tests unitarios del motor de notificaciones (sin Redis/Mongo reales)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from notifier.channels.email import EmailChannel
from notifier.channels.whatsapp import WhatsAppChannel
from notifier.engine import NotificationEngine, _norm_sev
from notifier.models import NotifPreferences, Recipient


def test_norm_sev():
    assert _norm_sev("CRÍTICA") == "critica"
    assert _norm_sev("ALTA") == "alta"
    assert _norm_sev(None) == "media"


@pytest.mark.asyncio
async def test_select_channels_critica_whatsapp_y_email():
    eng = NotificationEngine()
    r = Recipient(
        id="1",
        nombre="a",
        email="a@x.com",
        whatsapp_number="+5491100000000",
        preferencias=NotifPreferences(email_enabled=True, whatsapp_enabled=True),
    )
    ch = await eng._select_channels("critica", r, es_horario_silencio=True)
    assert "email" in ch and "whatsapp" in ch


@pytest.mark.asyncio
async def test_select_channels_alta_silencio_solo_email():
    eng = NotificationEngine()
    r = Recipient(
        id="1",
        nombre="a",
        email="a@x.com",
        whatsapp_number="+5491100000000",
        preferencias=NotifPreferences(email_enabled=True, whatsapp_enabled=True),
    )
    ch = await eng._select_channels("alta", r, es_horario_silencio=True)
    assert ch == ["email"]


@pytest.mark.asyncio
async def test_select_channels_usa_prefs_efectivas_cuando_manager_mockea():
    eng = NotificationEngine()
    r = Recipient(
        id="1",
        nombre="a",
        email="a@x.com",
        preferencias=NotifPreferences(email_enabled=True, whatsapp_enabled=True),
    )
    with patch.object(
        NotificationEngine,
        "_effective_prefs_for_recipient",
        new_callable=AsyncMock,
        return_value=NotifPreferences(email_enabled=False, whatsapp_enabled=False),
    ):
        ch = await eng._select_channels("media", r, es_horario_silencio=False)
    assert ch == []


@pytest.mark.asyncio
async def test_quiet_hours_skip_media_incident(monkeypatch):
    monkeypatch.setenv("NOTIFY_QUIET_START", "00:00")
    monkeypatch.setenv("NOTIFY_QUIET_END", "23:59")
    eng = NotificationEngine()
    assert eng._is_quiet_hours() is True

    eng.mongo = MagicMock()
    eng.mongo.db = {"notifications_log": MagicMock(insert_one=AsyncMock())}
    eng.redis_bus.client = MagicMock()
    eng.redis_bus.client.exists = AsyncMock(return_value=0)
    eng.redis_bus.client.incr = AsyncMock(return_value=1)
    eng.redis_bus.client.expire = AsyncMock(return_value=True)
    eng.redis_bus.client.set = AsyncMock(return_value=True)

    with patch.object(NotificationEngine, "_load_recipients", return_value=[]):
        await eng.process_event(
            "incidente_media",
            {"id": "i1", "severidad": "MEDIA", "dedup_key": "i1:media"},
        )


@pytest.mark.asyncio
async def test_honeypot_sin_dedup(monkeypatch):
    eng = NotificationEngine()
    eng._load_recipients = lambda: [
        Recipient(
            id="adm",
            nombre="Admin",
            email="a@x.com",
            es_admin=True,
            preferencias=NotifPreferences(),
        )
    ]
    eng.mongo = MagicMock()
    eng.mongo.db = {"notifications_log": MagicMock(insert_one=AsyncMock())}
    eng.redis_bus.client = MagicMock()
    eng.redis_bus.client.exists = AsyncMock(return_value=0)
    eng.redis_bus.client.incr = AsyncMock(side_effect=[1, 1])
    eng.redis_bus.client.expire = AsyncMock(return_value=True)
    eng.redis_bus.client.set = AsyncMock(return_value=True)

    with patch.object(EmailChannel, "send", new_callable=AsyncMock, return_value=True):
        with patch.object(WhatsAppChannel, "send", new_callable=AsyncMock, return_value=True):
            await eng.process_event("honeypot_hit", {"id": "hp1", "descripcion": "x"})
    eng.redis_bus.client.exists.assert_not_called()
