import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from api.models import Evento, EventoInterno, EventoExterno

# Modo asyncio estricto
pytest_plugins = ('pytest_asyncio',)

def pytest_configure(config):
    config.addinivalue_line(
        "markers", "integration: mark test to run only with real external/redis dependencies"
    )

@pytest.fixture
def evento_dns_sample():
    """Evento DNS válido de ejemplo alineado al modelo real de api/models.py"""
    return Evento(
        source="dns",
        tipo="query",
        interno=EventoInterno(
            ip="192.168.1.50",
            hostname="pc-it-01",
            usuario="usuario1",
            area="IT"
        ),
        externo=EventoExterno(
            valor="malicious-test.com",
            tipo="dominio"
        )
    )

@pytest.fixture
def evento_proxy_sample():
    """Evento Proxy válido de ejemplo"""
    return Evento(
        source="proxy",
        tipo="request",
        interno=EventoInterno(
            ip="192.168.1.100",
            hostname="pc-ventas-02",
            usuario="usuario2",
            area="Ventas"
        ),
        externo=EventoExterno(
            valor="http://suspicious-download.com/file.exe",
            tipo="url"
        )
    )

@pytest.fixture
def redis_mock():
    """
    Mock de RedisBus en memoria para tests unitarios.
    Simula set/get con un dict local, no requiere Redis real.
    """
    mock = AsyncMock()
    
    _store = {}

    async def fake_cache_set(key, val, ex=None):
        _store[key] = val

    async def fake_cache_get(key):
        return _store.get(key)

    mock.cache_set.side_effect = fake_cache_set
    mock.cache_get.side_effect = fake_cache_get
    mock.publish_enriched = AsyncMock()
    mock.publish_alert = AsyncMock()

    return mock

@pytest.fixture
async def redis_real():
    """
    Conexión real a Redis local. Solo para tests @pytest.mark.integration.
    """
    from shared.redis_bus import RedisBus
    bus = RedisBus()
    await bus.connect()
    yield bus
    await bus.r.aclose()
