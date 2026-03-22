"""Tests unitarios de modelos y quick_health con mocks."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from observability.health import ComponentHealth, HealthReport, quick_health


def test_health_report_model_dump_json():
    h = ComponentHealth(
        nombre="Redis",
        estado="ok",
        mensaje="Operativo",
        checked_at=datetime.now(timezone.utc),
    )
    r = HealthReport(
        estado_general="ok",
        componentes={"redis": h},
        servicios={},
        apis={},
        resumen="OK",
        generated_at=datetime.now(timezone.utc),
    )
    d = r.model_dump(mode="json")
    assert d["estado_general"] == "ok"
    assert d["componentes"]["redis"]["estado"] == "ok"


@pytest.mark.asyncio
async def test_quick_health_ok_with_mocks():
    redis_bus = MagicMock()
    redis_bus.client = MagicMock()
    redis_bus.client.ping = AsyncMock(return_value=True)
    redis_bus.client.info = AsyncMock(
        return_value={"used_memory_human": "1M", "connected_clients": 2}
    )
    redis_bus.connect = AsyncMock()

    mongo = MagicMock()
    mongo.db = MagicMock()
    mongo.db.events = MagicMock()
    mongo.db.events.count_documents = AsyncMock(return_value=0)
    mongo.connect = AsyncMock()
    mongo.ping = AsyncMock(return_value=True)

    async def fake_command(_cmd):
        return {"dataSize": 100, "indexSize": 50}

    mongo.db.command = AsyncMock(side_effect=fake_command)

    out = await quick_health(redis_bus, mongo)
    assert out["status"] == "ok"
    assert "timestamp" in out
