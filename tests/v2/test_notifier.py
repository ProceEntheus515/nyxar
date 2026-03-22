"""Tests V2: notifier (dedup, quiet hours, canales) con Redis emulado y envíos mockeados."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from notifier.channels.email import EmailChannel
from notifier.channels.whatsapp import WhatsAppChannel
from notifier.engine import NotificationEngine


@pytest.mark.v2
async def test_whatsapp_envia_critico(mongo_client_mock, redis_bus_fake, monkeypatch):
    monkeypatch.setenv("NOTIFY_ADMIN_EMAILS", "soc@example.com")
    monkeypatch.setenv("NOTIFY_ADMIN_WHATSAPP", "+15551234567")
    eng = NotificationEngine()
    eng.mongo = mongo_client_mock
    eng.redis_bus = redis_bus_fake
    eng._wa_ch.send = AsyncMock(return_value=True)
    eng._email_ch.send = AsyncMock(return_value=True)
    monkeypatch.setattr(eng, "_get_prefs_manager", AsyncMock(return_value=None))
    await eng.process_event(
        "incidente_detectado",
        {
            "id": "inc-wa-1",
            "severidad": "CRITICA",
            "titulo": "Critico",
            "descripcion": "x",
        },
    )
    eng._wa_ch.send.assert_awaited()


@pytest.mark.v2
async def test_email_envia_con_html(mongo_client_mock, redis_bus_fake, monkeypatch):
    monkeypatch.setenv("NOTIFY_SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("NOTIFY_ADMIN_EMAILS", "soc@example.com")
    captured: list = []

    async def fake_send_once(self, to_addr, mensaje):
        html = self._build_html(mensaje)
        captured.append(html)
        return True

    monkeypatch.setattr(EmailChannel, "_send_once", fake_send_once)
    eng = NotificationEngine()
    eng.mongo = mongo_client_mock
    eng.redis_bus = redis_bus_fake
    monkeypatch.setattr(eng, "_get_prefs_manager", AsyncMock(return_value=None))
    await eng.process_event(
        "incidente_detectado",
        {
            "id": "inc-mail-1",
            "severidad": "ALTA",
            "titulo": "Alta",
            "descripcion": "cuerpo",
        },
    )
    assert captured, "debe generarse HTML para el correo"
    assert "html" in (captured[0] or "").lower() or "<" in (captured[0] or "")


@pytest.mark.v2
def test_whatsapp_trunca_mensaje():
    largo = "A" * 300
    corto = WhatsAppChannel._truncate_for_whatsapp(largo, max_len=200)
    assert len(corto) <= 200
    assert corto.endswith("...")


@pytest.mark.v2
@pytest.mark.integration
async def test_dedup_previene_repeticion(mongo_client_mock, redis_bus_fake, monkeypatch):
    monkeypatch.setenv("NOTIFY_ADMIN_EMAILS", "soc@example.com")
    eng = NotificationEngine()
    eng.mongo = mongo_client_mock
    eng.redis_bus = redis_bus_fake
    eng._email_ch.send = AsyncMock(return_value=True)
    eng._wa_ch.send = AsyncMock(return_value=True)
    monkeypatch.setattr(eng, "_get_prefs_manager", AsyncMock(return_value=None))
    payload = {"id": "inc-dedup-1", "severidad": "ALTA", "titulo": "t", "descripcion": "d"}
    await eng.process_event("incidente_detectado", payload)
    await eng.process_event("incidente_detectado", payload)
    assert eng._email_ch.send.await_count == 1


@pytest.mark.v2
async def test_quiet_hours_bloquea_medio(mongo_client_mock, redis_bus_fake, monkeypatch):
    monkeypatch.setenv("NOTIFY_SECURITY_EMAILS", "sec@example.com")
    eng = NotificationEngine()
    eng.mongo = mongo_client_mock
    eng.redis_bus = redis_bus_fake
    eng._email_ch.send = AsyncMock(return_value=True)
    monkeypatch.setattr(eng, "_get_prefs_manager", AsyncMock(return_value=None))
    monkeypatch.setattr(eng, "_is_quiet_hours", lambda: True)
    await eng.process_event(
        "incidente_detectado",
        {"id": "inc-q-1", "severidad": "MEDIA", "titulo": "m", "descripcion": "d"},
    )
    eng._email_ch.send.assert_not_awaited()


@pytest.mark.v2
async def test_quiet_hours_no_bloquea_critico(mongo_client_mock, redis_bus_fake, monkeypatch):
    monkeypatch.setenv("NOTIFY_ADMIN_EMAILS", "admin@example.com")
    eng = NotificationEngine()
    eng.mongo = mongo_client_mock
    eng.redis_bus = redis_bus_fake
    eng._email_ch.send = AsyncMock(return_value=True)
    eng._wa_ch.send = AsyncMock(return_value=True)
    monkeypatch.setattr(eng, "_get_prefs_manager", AsyncMock(return_value=None))
    monkeypatch.setattr(eng, "_is_quiet_hours", lambda: True)
    await eng.process_event(
        "incidente_detectado",
        {"id": "inc-q-2", "severidad": "CRITICA", "titulo": "c", "descripcion": "d"},
    )
    assert eng._email_ch.send.await_count >= 1 or eng._wa_ch.send.await_count >= 1


@pytest.mark.v2
async def test_canal_falla_intenta_siguiente(mongo_client_mock, redis_bus_fake, monkeypatch):
    monkeypatch.setenv("NOTIFY_ADMIN_EMAILS", "a@example.com")
    monkeypatch.setenv("NOTIFY_ADMIN_WHATSAPP", "+15559876543")
    eng = NotificationEngine()
    eng.mongo = mongo_client_mock
    eng.redis_bus = redis_bus_fake
    monkeypatch.setattr(eng, "_get_prefs_manager", AsyncMock(return_value=None))
    eng._wa_ch.send = AsyncMock(return_value=False)
    eng._email_ch.send = AsyncMock(return_value=True)
    await eng.process_event(
        "incidente_detectado",
        {"id": "inc-fb-1", "severidad": "CRITICA", "titulo": "t", "descripcion": "d"},
    )
    eng._email_ch.send.assert_awaited()


@pytest.mark.v2
async def test_honeypot_siempre_envia(mongo_client_mock, redis_bus_fake, monkeypatch):
    monkeypatch.setenv("NOTIFY_ADMIN_EMAILS", "admin@example.com")
    eng = NotificationEngine()
    eng.mongo = mongo_client_mock
    eng.redis_bus = redis_bus_fake
    eng._email_ch.send = AsyncMock(return_value=True)
    monkeypatch.setattr(eng, "_get_prefs_manager", AsyncMock(return_value=None))
    monkeypatch.setattr(eng, "_is_quiet_hours", lambda: True)
    await eng.process_event(
        "honeypot_hit",
        {"id": "hp-1", "severidad": "MEDIA", "titulo": "Honey", "descripcion": "touch"},
    )
    eng._email_ch.send.assert_awaited()
