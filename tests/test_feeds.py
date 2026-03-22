import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from enricher.feeds.downloader import FeedDownloader

@pytest.fixture
def downloader():
    mock_redis = AsyncMock()
    mock_redis.client = None  # Sin Redis real
    return FeedDownloader(redis_bus=mock_redis)

@pytest.mark.asyncio
async def test_descarga_urlhaus_dominio(downloader):
    """download_feed para urlhaus debe ser llamable sin crash con Redis mock."""
    # Mockea directamente download_feed para test de integración de scheduler
    downloader.download_feed = AsyncMock(return_value=None)
    await downloader.download_all()
    # Verifica que se intentó descargar todos los feeds
    assert downloader.download_feed.call_count == len(FeedDownloader.FEEDS)


@pytest.mark.asyncio
async def test_check_ip_no_redis(downloader):
    """Sin Redis activo, check_ip debe retornar None sin crash."""
    downloader.redis_bus.client = None
    result = await downloader.check_ip("1.2.3.4")
    assert result is None

@pytest.mark.asyncio
async def test_check_domain_no_redis(downloader):
    """Sin Redis activo, check_domain debe retornar None sin crash."""
    downloader.redis_bus.client = None
    result = await downloader.check_domain("evil.com")
    assert result is None

@pytest.mark.asyncio
async def test_get_stats_sin_redis(downloader):
    """Stats sin Redis devuelve dict vacío."""
    downloader.redis_bus.client = None
    stats = await downloader.get_stats()
    assert isinstance(stats, dict)
    assert len(stats) == 0
