"""Tests unitarios de IdentityResolver (sin Mongo/Redis reales)."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from ad_connector.resolver import IdentityResolver, SESSION_PREFIX


@pytest.mark.asyncio
@pytest.mark.unit
async def test_resolve_cache_hit():
    redis_bus = AsyncMock()
    redis_bus.cache_get = AsyncMock(
        return_value={
            "ip": "10.0.0.1",
            "usuario": "ana",
            "hostname": "PC1",
            "area": "it",
            "nombre_completo": None,
            "cargo": None,
            "es_privilegiado": False,
            "fuente_resolucion": "wazuh_logon",
        }
    )
    mongo = MagicMock()
    r = IdentityResolver(redis_bus, mongo)
    out = await r.resolve("10.0.0.1")
    assert out["fuente_resolucion"] == "cache"
    assert out["usuario"] == "ana"
    redis_bus.cache_set.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.unit
async def test_resolve_wazuh_logons_miss_then_identity():
    redis_bus = AsyncMock()
    redis_bus.cache_get = AsyncMock(return_value=None)
    redis_bus.cache_set = AsyncMock()

    wazuh_col = MagicMock()
    wazuh_col.find_one = AsyncMock(return_value=None)

    ident_col = MagicMock()
    ident_col.find_one = AsyncMock(
        side_effect=[
            {
                "usuario": "bob",
                "nombre_completo": "Bob",
                "hostname": "H1",
                "area": "ventas",
                "cargo": "Dev",
                "es_privilegiado": False,
            },
            None,
        ]
    )

    db = MagicMock()
    db.wazuh_logons = wazuh_col
    db.identities = ident_col

    mongo = MagicMock()
    mongo.db = db

    r = IdentityResolver(redis_bus, mongo)
    out = await r.resolve("192.168.1.10")

    assert out["usuario"] == "bob"
    assert out["fuente_resolucion"] == "ad_sync"
    assert out["ip"] == "192.168.1.10"
    redis_bus.cache_set.assert_called_once()
    call_args = redis_bus.cache_set.call_args
    assert call_args[0][0] == f"{SESSION_PREFIX}192.168.1.10"
    assert call_args[1].get("ttl") == 300


@pytest.mark.asyncio
@pytest.mark.unit
async def test_resolve_mongo_timeout_returns_unknown():
    redis_bus = AsyncMock()
    redis_bus.cache_get = AsyncMock(return_value=None)
    redis_bus.cache_set = AsyncMock()

    async def slow_find_one(*a, **k):
        import asyncio

        await asyncio.sleep(1.0)
        return None

    wazuh_col = MagicMock()
    wazuh_col.find_one = slow_find_one
    ident_col = MagicMock()
    ident_col.find_one = AsyncMock(return_value=None)
    db = MagicMock()
    db.wazuh_logons = wazuh_col
    db.identities = ident_col
    mongo = MagicMock()
    mongo.db = db

    r = IdentityResolver(redis_bus, mongo)
    out = await r.resolve("192.168.1.20")
    assert out["fuente_resolucion"] == "desconocido"
    assert out["usuario"] == "desconocido"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_invalidate_calls_delete():
    redis_bus = AsyncMock()
    redis_bus.cache_delete = AsyncMock()
    mongo = MagicMock()
    r = IdentityResolver(redis_bus, mongo)
    await r.invalidate("10.0.0.5")
    redis_bus.cache_delete.assert_called_once_with(f"{SESSION_PREFIX}10.0.0.5")


@pytest.mark.asyncio
@pytest.mark.unit
async def test_get_all_active_sessions():
    redis_bus = AsyncMock()
    redis_bus.cache_scan_keys = AsyncMock(
        return_value=[f"{SESSION_PREFIX}10.0.0.1", f"{SESSION_PREFIX}10.0.0.2"]
    )
    redis_bus.cache_get = AsyncMock(
        side_effect=[
            {"ip": "10.0.0.1", "usuario": "a"},
            {"ip": "10.0.0.2", "usuario": "b"},
        ]
    )
    mongo = MagicMock()
    r = IdentityResolver(redis_bus, mongo)
    rows = await r.get_all_active_sessions()
    assert len(rows) == 2


@pytest.mark.unit
def test_event_field_mapping_in_normalizer():
    from collector.normalizer import _event_field_from_resolver

    assert _event_field_from_resolver("desconocido") == "unknown"
    assert _event_field_from_resolver("x") == "x"
