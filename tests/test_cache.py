import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from enricher.cache import EnrichmentCache
from api.models import Enrichment

@pytest.fixture
def cache():
    """EnrichmentCache con RedisBus completamente mockeado."""
    mock_redis = AsyncMock()
    mock_redis.client = None  # Sin Redis real por default
    
    # Cache en memoria para simular set/get
    _store = {}
    async def fake_cache_get(key):
        return _store.get(key)
    async def fake_cache_set(key, val, ttl=None):
        _store[key] = val
    
    mock_redis.cache_get.side_effect = fake_cache_get
    mock_redis.cache_set.side_effect = fake_cache_set
    
    c = EnrichmentCache(redis_bus=mock_redis)
    return c

def _make_enrichment(score=85, malicious=True):
    return Enrichment(
        reputacion="malicioso" if malicious else "limpio",
        fuente="test",
        tags=["malware"] if malicious else []
    )

@pytest.mark.asyncio
async def test_cache_set_get(cache):
    """Guardar un Enrichment y recuperarlo."""
    enr = _make_enrichment(score=85, malicious=True)
    await cache.set_enrichment("8.8.8.8", enr, ttl_seconds=3600)
    res = await cache.get_enrichment("8.8.8.8")
    assert res is not None
    assert res.reputacion == "malicioso"

@pytest.mark.asyncio
async def test_cache_miss(cache):
    """Key inexistente → None."""
    res = await cache.get_enrichment("no-existe.com")
    assert res is None

@pytest.mark.asyncio
async def test_cache_ttl_simulated(cache):
    """Post-TTL, simulamos que cache_get retorna None (como si la key expiró)."""
    enr = _make_enrichment()
    await cache.set_enrichment("timeout-test.com", enr, ttl_seconds=1)
    
    # Simulamos vencimiento: forzamos cache_get a retornar None
    cache.redis_bus.cache_get = AsyncMock(return_value=None)
    res = await cache.get_enrichment("timeout-test.com")
    assert res is None

@pytest.mark.asyncio
async def test_cache_stats_sin_redis(cache):
    """Sin Redis real, get_stats devuelve vacío sin crash."""
    cache.redis_bus.client = None
    stats = await cache.get_stats()
    assert isinstance(stats, dict)

@pytest.mark.asyncio
async def test_cache_stats_con_redis_mock(cache):
    """Con Redis mock, hit_rate_pct se calcula correctamente."""
    r_mock = AsyncMock()
    r_mock.get = AsyncMock(side_effect=[b"3", b"7"])   # 3 hits, 7 misses → 30%
    r_mock.scan = AsyncMock(return_value=(b"0", [b"enrich:a", b"enrich:b"]))   # 2 keys
    cache.redis_bus.client = r_mock
    
    stats = await cache.get_stats()
    assert stats["hits"] == 3
    assert stats["misses"] == 7
    assert stats["hit_rate_pct"] == 30.0
    assert stats["total_keys"] == 2
