import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from enricher.main import EnrichmentEngine
from api.models import Evento, EventoInterno, EventoExterno, Enrichment

@pytest.fixture
def engine():
    """
    EnrichmentEngine con todos sus colaboradores mockeados.
    Evitamos instanciar RedisBus real en cada test.
    """
    with patch("enricher.main.RedisBus") as MockRedis, \
         patch("enricher.main.EnrichmentCache") as MockCache, \
         patch("enricher.main.FeedDownloader") as MockFeeds, \
         patch("enricher.main.AbuseIPDB") as MockAbuse, \
         patch("enricher.main.AlienVaultOTX") as MockOTX:

        eng = EnrichmentEngine()

        # Configurar mocks útiles por defecto
        eng.cache = AsyncMock()
        eng.feeds = AsyncMock()
        eng.abuse_ipdb = AsyncMock()
        eng.otx = AsyncMock()

        # Por defecto: cache miss, feeds sin match, APIs sin datos
        eng.cache.get_enrichment = AsyncMock(return_value=None)
        eng.cache.set_enrichment = AsyncMock()
        eng.cache.record_hit = AsyncMock()
        eng.cache.record_miss = AsyncMock()
        eng.feeds.check_ip = AsyncMock(return_value=None)
        eng.feeds.check_domain = AsyncMock(return_value=None)
        eng.abuse_ipdb.check_ip = AsyncMock(return_value=None)
        eng.otx.check_indicator = AsyncMock(return_value=None)

        yield eng

def _make_evento(tipo_externo="dominio", valor="evil.com"):
    return Evento(
        source="dns",
        tipo="query",
        interno=EventoInterno(ip="192.168.1.10", hostname="pc01", usuario="user", area="IT"),
        externo=EventoExterno(valor=valor, tipo=tipo_externo)
    )

def _make_enrichment(reputacion="malicioso"):
    return Enrichment(reputacion=reputacion, fuente="test-source", tags=["test"])

@pytest.mark.asyncio
async def test_enrich_ip_en_cache(engine):
    """Si el Enrichment ya está en caché, no consulta APIs."""
    cached = _make_enrichment("malicioso")
    engine.cache.get_enrichment = AsyncMock(return_value=cached)

    ev = _make_evento(tipo_externo="ip", valor="1.2.3.4")
    result = await engine.enrich_event(ev)

    assert result.enrichment is not None
    assert result.enrichment.reputacion == "malicioso"
    engine.abuse_ipdb.check_ip.assert_not_called()
    engine.otx.check_indicator.assert_not_called()

@pytest.mark.asyncio
async def test_enrich_ip_en_blocklist(engine):
    """IP encontrada en blocklist local → no llama APIs externas."""
    engine.feeds.check_ip = AsyncMock(return_value="spamhaus_drop")

    ev = _make_evento(tipo_externo="ip", valor="5.5.5.5")
    result = await engine.enrich_event(ev)

    assert result.enrichment is not None
    assert result.enrichment.reputacion == "malicioso"
    assert "Local Blocklist" in result.enrichment.fuente
    engine.abuse_ipdb.check_ip.assert_not_called()

@pytest.mark.asyncio
async def test_enrich_ip_limpia(engine):
    """IP limpia → consulta AbuseIPDB y retorna limpio."""
    enrich_limpio = _make_enrichment("limpio")
    engine.abuse_ipdb.check_ip = AsyncMock(return_value=enrich_limpio)

    ev = _make_evento(tipo_externo="ip", valor="8.8.8.8")
    result = await engine.enrich_event(ev)

    assert result.enrichment.reputacion == "limpio"
    engine.abuse_ipdb.check_ip.assert_called_once_with("8.8.8.8")

@pytest.mark.asyncio
async def test_enrich_dominio_blocklist(engine):
    """Dominio encontrado en URLHaus blocklist local."""
    engine.feeds.check_domain = AsyncMock(return_value="urlhaus_domains")

    ev = _make_evento(tipo_externo="dominio", valor="evil.com")
    result = await engine.enrich_event(ev)

    assert result.enrichment.reputacion == "malicioso"
    assert "Local Blocklist" in result.enrichment.fuente

@pytest.mark.asyncio
async def test_enrich_api_falla_usa_siguiente(engine):
    """AbuseIPDB falla → usa OTX como segunda opción."""
    engine.abuse_ipdb.check_ip = AsyncMock(side_effect=Exception("Rate limit 429"))
    enrich_otx = _make_enrichment("sospechoso")
    engine.otx.check_indicator = AsyncMock(return_value=enrich_otx)

    ev = _make_evento(tipo_externo="ip", valor="9.9.9.9")
    result = await engine.enrich_event(ev)

    assert result.enrichment is not None
    engine.otx.check_indicator.assert_called_once()

@pytest.mark.asyncio
async def test_enrich_todas_apis_fallan_fallback(engine):
    """Todas las APIs fallan → fallback a 'desconocido', no lanza excepción."""
    engine.abuse_ipdb.check_ip = AsyncMock(side_effect=asyncio.TimeoutError())
    engine.otx.check_indicator = AsyncMock(side_effect=asyncio.TimeoutError())

    ev = _make_evento(tipo_externo="ip", valor="10.20.30.40")
    result = await engine.enrich_event(ev)

    # Debe retornar siempre un evento, aunque sea con desconocido
    assert result is not None
    assert result.enrichment is not None
    assert result.enrichment.reputacion in ("desconocido", "limpio")

@pytest.mark.asyncio
async def test_enrich_guarda_en_cache(engine):
    """Tras enriquecer exitosamente, debe guardar en caché."""
    enrich_result = _make_enrichment("sospechoso")
    engine.otx.check_indicator = AsyncMock(return_value=enrich_result)

    ev = _make_evento(tipo_externo="dominio", valor="suspicious.com")
    await engine.enrich_event(ev)

    engine.cache.set_enrichment.assert_called_once()
