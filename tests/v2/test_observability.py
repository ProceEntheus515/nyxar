"""Tests V2: observability (health, métricas) sin servicios externos reales."""

from __future__ import annotations

import time
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from observability.health import ComponentHealth, HealthChecker, HealthReport, _now, quick_health
from observability.main import metrics_endpoint


@pytest.mark.v2
async def test_heartbeat_detecta_servicio_caido(redis_bus_fake, mongo_client_mock):
    checker = HealthChecker(redis_bus_fake, mongo_client_mock)
    h = await checker._heartbeat_component("collector")
    assert h.estado == "critical"
    assert "heartbeat" in (h.mensaje or "").lower() or "sin" in (h.mensaje or "").lower()


@pytest.mark.v2
async def test_redis_check_latencia(redis_bus_fake, mongo_client_mock):
    checker = HealthChecker(redis_bus_fake, mongo_client_mock)
    h = await checker.check_redis()
    assert h.estado == "ok"
    assert h.latencia_ms is not None
    assert h.latencia_ms >= 0


@pytest.mark.v2
async def test_pipeline_sin_eventos_warning(redis_bus_fake, mongo_client_mock):
    await mongo_client_mock.db.events.insert_one(
        {
            "id": "ev-old",
            "timestamp": "2025-01-01T00:00:00+00:00",
        }
    )
    base = datetime(2025, 1, 1, 0, 20, 0, tzinfo=timezone.utc)
    checker = HealthChecker(redis_bus_fake, mongo_client_mock)

    async def no_stream(_stream: str):
        return None

    redis_bus_fake.stream_latest_payload = no_stream

    with patch("observability.health._now", return_value=base):
        h = await checker.check_pipeline()
    assert h.estado == "warning"


@pytest.mark.v2
async def test_pipeline_sin_eventos_critico(redis_bus_fake, mongo_client_mock):
    await mongo_client_mock.db.events.insert_one(
        {
            "id": "ev-old2",
            "timestamp": "2025-01-01T00:00:00+00:00",
        }
    )
    base = datetime(2025, 1, 1, 0, 45, 0, tzinfo=timezone.utc)
    checker = HealthChecker(redis_bus_fake, mongo_client_mock)

    async def no_stream(_stream: str):
        return None

    redis_bus_fake.stream_latest_payload = no_stream

    with patch("observability.health._now", return_value=base):
        h = await checker.check_pipeline()
    assert h.estado == "critical"


@pytest.mark.v2
async def test_health_report_formato(redis_bus_fake, mongo_client_mock):
    checker = HealthChecker(redis_bus_fake, mongo_client_mock)

    async def apis_stub(self):
        ts = _now()
        return {
            "abuseipdb": ComponentHealth(
                nombre="AbuseIPDB",
                estado="unknown",
                mensaje="API no configurada",
                detalles={},
                checked_at=ts,
            ),
            "otx": ComponentHealth(
                nombre="OTX",
                estado="unknown",
                mensaje="API no configurada",
                detalles={},
                checked_at=ts,
            ),
            "anthropic": ComponentHealth(
                nombre="Anthropic",
                estado="unknown",
                mensaje="API no configurada",
                detalles={},
                checked_at=ts,
            ),
            "misp": ComponentHealth(
                nombre="MISP",
                estado="unknown",
                mensaje="API no configurada",
                detalles={},
                checked_at=ts,
            ),
        }

    with patch.object(HealthChecker, "check_apis", apis_stub):
        with patch.object(HealthChecker, "check_services", new_callable=AsyncMock) as svc:
            svc.return_value = {
                "collector": await checker._heartbeat_component("collector"),
            }
            report = await checker.full_check()
    assert isinstance(report, HealthReport)
    assert report.estado_general in ("ok", "degradado", "critico")
    assert "redis" in report.componentes
    assert report.resumen
    assert report.generated_at


@pytest.mark.v2
async def test_metricas_prometheus_expuestas():
    resp = await metrics_endpoint()
    raw = resp.body
    text = raw.decode() if isinstance(raw, (bytes, bytearray)) else str(raw)
    assert "#" in text or "TYPE" in text.upper()


@pytest.mark.v2
async def test_health_endpoint_rapido(redis_bus_fake, mongo_client_mock):
    t0 = time.perf_counter()
    q = await quick_health(redis_bus_fake, mongo_client_mock)
    elapsed_ms = (time.perf_counter() - t0) * 1000
    assert "status" in q
    assert elapsed_ms < 800
