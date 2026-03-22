"""Tests MISPIngestor con Redis emulado."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from misp_connector.ingestor import KEY_LAST_SYNC, MISPIngestor


@pytest.mark.v2
@pytest.mark.asyncio
async def test_ingest_ips_carga_blocklist(redis_bus_fake, misp_env):
    rows = [
        {
            "attribute": {"type": "ip-dst", "value": "203.0.113.5"},
            "event": {"info": "E1", "threat_level_id": 1, "Tag": []},
        }
    ]
    client = MagicMock()
    client.get_attributes = AsyncMock(return_value=rows)

    ing = MISPIngestor(redis_bus=redis_bus_fake)
    await redis_bus_fake.connect()
    await ing.sync_once(client)

    r = redis_bus_fake.client
    assert "203.0.113.5" in r._sets["blocklist:misp_ips"]
    meta = await redis_bus_fake.cache_get("misp:meta:203.0.113.5")
    assert meta is not None
    assert meta.get("reputacion") == "malicioso"


@pytest.mark.v2
@pytest.mark.asyncio
async def test_ingest_no_duplica(redis_bus_fake, misp_env):
    row = {
        "attribute": {"type": "ip-dst", "value": "198.51.100.2"},
        "event": {"threat_level_id": 2},
    }
    client = MagicMock()
    client.get_attributes = AsyncMock(return_value=[row, row])

    ing = MISPIngestor(redis_bus=redis_bus_fake)
    await redis_bus_fake.connect()
    stats = await ing.sync_once(client)
    assert stats["nuevos"] == 1
    assert len(redis_bus_fake.client._sets["blocklist:misp_ips"]) == 1


@pytest.mark.v2
@pytest.mark.asyncio
async def test_contexto_guardado(redis_bus_fake, misp_env):
    rows = [
        {
            "attribute": {"type": "domain", "value": "bad.example", "Tag": [{"name": "tlp:red"}]},
            "event": {"info": "Camp", "threat_level_id": 2},
        }
    ]
    client = MagicMock()
    client.get_attributes = AsyncMock(return_value=rows)
    ing = MISPIngestor(redis_bus=redis_bus_fake)
    await redis_bus_fake.connect()
    await ing.sync_once(client)
    meta = await redis_bus_fake.cache_get("misp:meta:bad.example")
    assert meta and meta.get("event_name") == "Camp"


@pytest.mark.v2
def test_map_threat_level():
    ing = MISPIngestor()
    assert ing._map_threat_level(1) == "malicioso"
    assert ing._map_threat_level(3) == "sospechoso"


@pytest.mark.v2
@pytest.mark.asyncio
async def test_sync_incremental_timestamp(redis_bus_fake, misp_env):
    past = datetime(2020, 1, 1, tzinfo=timezone.utc).isoformat()
    await redis_bus_fake.connect()
    await redis_bus_fake.client.set(KEY_LAST_SYNC, past)

    client = MagicMock()
    client.get_attributes = AsyncMock(return_value=[])

    ing = MISPIngestor(redis_bus=redis_bus_fake)
    await ing.sync_once(client)
    client.get_attributes.assert_awaited()
    call_kw = client.get_attributes.await_args.kwargs
    assert "publish_timestamp" in call_kw
