"""Tests de PreferencesManager (merge, validación admin, Mongo/Redis mock)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from notifier.preferences_manager import (
    PreferencesManager,
    _merge_severity_layers,
    _parse_channels_enabled,
    is_preference_admin_user,
    validate_user_prefs_not_stripping_critica_admin,
)


def test_merge_severity_layers_defaults():
    m = _merge_severity_layers()
    assert m["critica"]["email_enabled"] is True
    assert m["critica"]["whatsapp_enabled"] is True
    assert m["info"]["email_enabled"] is False


def test_merge_severity_layers_global_mask(monkeypatch):
    monkeypatch.setenv("NOTIFY_CHANNELS_ENABLED", "email")
    m = _merge_severity_layers()
    assert m["critica"]["email_enabled"] is True
    assert m["critica"]["whatsapp_enabled"] is False


def test_is_preference_admin_user(monkeypatch):
    monkeypatch.setenv("NOTIFY_ADMIN_EMAILS", "boss@x.com")
    monkeypatch.setenv("NOTIFY_PREFERENCE_ADMIN_IDS", "u-1")
    assert is_preference_admin_user("boss@x.com") is True
    assert is_preference_admin_user("u-1") is True
    assert is_preference_admin_user("other@x.com") is False


def test_validate_admin_critica_both_off(monkeypatch):
    monkeypatch.setenv("NOTIFY_ADMIN_EMAILS", "admin@x.com")
    merged = {
        "critica": {"email_enabled": False, "whatsapp_enabled": False},
    }
    with pytest.raises(ValueError, match="administradores"):
        validate_user_prefs_not_stripping_critica_admin("admin@x.com", merged)


class _FakeMongoDB:
    def __init__(self, col: MagicMock) -> None:
        self._col = col

    def __getitem__(self, _name: str) -> MagicMock:
        return self._col


@pytest.mark.asyncio
async def test_get_for_recipient_uses_defaults_when_empty_db():
    col = MagicMock()
    col.find_one = AsyncMock(return_value=None)
    col.create_index = AsyncMock()
    col.update_one = AsyncMock()
    col.delete_one = AsyncMock()

    db = _FakeMongoDB(col)

    redis = MagicMock()
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock()

    pm = PreferencesManager(db, lambda: redis)
    p = await pm.get_for_recipient("user-1", "media", area=None)
    assert p.email_enabled is True
    assert p.whatsapp_enabled is False


@pytest.mark.asyncio
async def test_set_user_preferences_merges_and_bumps_gen(monkeypatch):
    monkeypatch.setenv("NOTIFY_ADMIN_EMAILS", "")
    stored: dict = {}

    async def find_one(filter_q: dict):
        if filter_q.get("scope") == "user" and filter_q.get("key") == "u1" and "severities" in stored:
            return {"severities": stored["severities"], "scope": "user", "key": "u1"}
        return None

    async def update_one(_filter_q: dict, update: dict, upsert: bool = False):
        stored["severities"] = update["$set"]["severities"]

    col = MagicMock()
    col.find_one = AsyncMock(side_effect=find_one)
    col.update_one = AsyncMock(side_effect=update_one)
    col.create_index = AsyncMock()
    col.delete_one = AsyncMock()

    db = _FakeMongoDB(col)

    redis = MagicMock()
    redis.get = AsyncMock(return_value="0")
    redis.incr = AsyncMock(return_value=1)

    pm = PreferencesManager(db, lambda: redis)
    await pm.set_user_preferences("u1", {"alta": {"email_enabled": False, "whatsapp_enabled": True}})
    redis.incr.assert_called()
    assert "alta" in stored["severities"]


@pytest.mark.asyncio
async def test_set_global_rejects_critica_all_off():
    col = MagicMock()
    col.find_one = AsyncMock(return_value=None)
    col.update_one = AsyncMock()
    col.create_index = AsyncMock()
    col.delete_one = AsyncMock()
    db = _FakeMongoDB(col)
    pm = PreferencesManager(db, lambda: None)
    with pytest.raises(ValueError, match="critica"):
        await pm.set_global_preferences(
            {"critica": {"email_enabled": False, "whatsapp_enabled": False}}
        )


def test_parse_channels_enabled_default(monkeypatch):
    monkeypatch.delenv("NOTIFY_CHANNELS_ENABLED", raising=False)
    assert _parse_channels_enabled() == {"email", "whatsapp"}
