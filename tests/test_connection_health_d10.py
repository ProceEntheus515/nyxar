"""Tests D10: salud de conexiones y rotacion de CA."""

from __future__ import annotations

import hashlib
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from nyxar.discovery.connection_health import (
    CA_FINGERPRINT_CACHE_KEY,
    AdaptiveConnectionHealth,
    ConnectionChangedError,
)
from nyxar.discovery.engine import InfrastructureMap


@pytest.mark.asyncio
async def test_check_ca_first_run_sets_cache(tmp_path: Path) -> None:
    cert = tmp_path / "ca.pem"
    cert.write_bytes(b"version-a")
    infra = InfrastructureMap(ca_cert_path=str(cert))
    bus = MagicMock()
    bus.client = object()
    bus.cache_get = AsyncMock(return_value=None)
    bus.cache_set = AsyncMock()
    health = AdaptiveConnectionHealth(infra, redis_bus=bus, check_interval_s=99999.0)
    await health._check_ca_cert(infra)
    bus.cache_set.assert_awaited()
    call_kw = bus.cache_set.await_args
    assert call_kw[0][0] == CA_FINGERPRINT_CACHE_KEY
    assert call_kw[0][1]["fingerprint"] == hashlib.sha256(b"version-a").hexdigest()


@pytest.mark.asyncio
async def test_check_ca_rotation_raises(tmp_path: Path) -> None:
    cert = tmp_path / "ca.pem"
    cert.write_bytes(b"v1")
    infra = InfrastructureMap(ca_cert_path=str(cert))
    fp1 = hashlib.sha256(b"v1").hexdigest()
    bus = MagicMock()
    bus.client = object()
    bus.cache_get = AsyncMock(return_value={"fingerprint": fp1})
    bus.cache_set = AsyncMock()
    health = AdaptiveConnectionHealth(infra, redis_bus=bus, check_interval_s=99999.0)
    cert.write_bytes(b"v2")
    with pytest.raises(ConnectionChangedError) as ei:
        await health._check_ca_cert(infra)
    assert ei.value.component == "tls_ca"


@pytest.mark.asyncio
async def test_check_dns_failure_raises() -> None:
    infra = InfrastructureMap(dns_server="192.0.2.1")
    health = AdaptiveConnectionHealth(infra, redis_bus=None, check_interval_s=99999.0)
    with patch.object(health, "_tcp_open", return_value=False):
        with pytest.raises(ConnectionChangedError) as ei:
            await health._check_dns(infra)
    assert ei.value.component == "dns"


@pytest.mark.asyncio
async def test_handle_connection_changed_triggers_rediscover() -> None:
    infra = InfrastructureMap(proxy_present=True, proxy_host="127.0.0.1", proxy_port=1)
    health = AdaptiveConnectionHealth(infra, redis_bus=None, check_interval_s=99999.0)
    with patch.object(health, "_rediscover_component", new_callable=AsyncMock) as rd:
        with patch.object(health, "_publish_alert", new_callable=AsyncMock):
            err = ConnectionChangedError("proxy", "test")
            await health._handle_connection_changed(err)
    rd.assert_awaited_once()
