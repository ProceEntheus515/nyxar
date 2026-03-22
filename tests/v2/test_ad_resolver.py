"""Tests IdentityResolver (cache, wazuh, invalidate)."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from ad_connector.resolver import IdentityResolver


@pytest.mark.v2
@pytest.mark.asyncio
async def test_resolve_desde_cache(redis_bus_fake, mongo_client_mock):
    ip = "10.10.10.10"
    await redis_bus_fake.connect()
    await redis_bus_fake.cache_set(
        "identity:session:" + ip,
        {
            "ip": ip,
            "usuario": "cached_user",
            "hostname": "pc1",
            "area": "IT",
            "cargo": None,
            "es_privilegiado": False,
            "fuente_resolucion": "wazuh_logon",
        },
        ttl=300,
    )
    r = IdentityResolver(redis_bus_fake, mongo_client_mock)
    out = await r.resolve(ip)
    assert out["usuario"] == "cached_user"
    assert out["fuente_resolucion"] == "cache"


@pytest.mark.v2
@pytest.mark.asyncio
async def test_resolve_desde_wazuh(redis_bus_fake, mongo_client_mock, mem_db):
    ip = "10.20.20.20"
    await mem_db.wazuh_logons.insert_one(
        {
            "ip": ip,
            "usuario": "w_user",
            "hostname": "ws1",
            "ts": datetime.now(timezone.utc),
        }
    )
    r = IdentityResolver(redis_bus_fake, mongo_client_mock)
    out = await r.resolve(ip)
    assert out["usuario"] == "w_user"
    assert out["fuente_resolucion"] == "wazuh_logon"


@pytest.mark.v2
@pytest.mark.asyncio
async def test_resolve_ip_desconocida(redis_bus_fake, mongo_client_mock):
    r = IdentityResolver(redis_bus_fake, mongo_client_mock)
    out = await r.resolve("10.99.99.99")
    assert out["usuario"] == "desconocido"


@pytest.mark.v2
@pytest.mark.asyncio
async def test_invalidate_limpia_cache(redis_bus_fake, mongo_client_mock, mem_db):
    ip = "10.30.30.30"
    await redis_bus_fake.connect()
    await redis_bus_fake.cache_set(
        "identity:session:" + ip,
        {
            "ip": ip,
            "usuario": "old",
            "hostname": "h",
            "area": "x",
            "cargo": None,
            "es_privilegiado": False,
            "fuente_resolucion": "cache",
        },
        ttl=300,
    )
    await mem_db.wazuh_logons.insert_one(
        {"ip": ip, "usuario": "fresh", "hostname": "h2", "ts": datetime.now(timezone.utc)}
    )
    r = IdentityResolver(redis_bus_fake, mongo_client_mock)
    await r.invalidate(ip)
    out = await r.resolve(ip)
    assert out["usuario"] == "fresh"


@pytest.mark.v2
@pytest.mark.asyncio
async def test_ip_servidor_resuelve_hostname(redis_bus_fake, mongo_client_mock, mem_db):
    ip = "10.40.40.40"
    await mem_db.wazuh_logons.insert_one(
        {
            "ip": ip,
            "usuario": "desconocido",
            "hostname": "SRV-DB01",
            "ts": datetime.now(timezone.utc),
        }
    )
    await mem_db.identities.insert_one(
        {
            "id": "c1",
            "tipo": "computer",
            "usuario": "SRV-DB01",
            "hostname": "SRV-DB01",
            "area": "Infra",
            "ip_asociada": "",
        }
    )
    r = IdentityResolver(redis_bus_fake, mongo_client_mock)
    out = await r.resolve(ip)
    assert out["area"] == "Infra" or out["hostname"] == "SRV-DB01"
