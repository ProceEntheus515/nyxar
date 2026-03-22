"""
Servicio de métricas Prometheus y health check NYXAR.

Ejecución local (desde la raíz del repo):
  set PYTHONPATH=.
  python -m uvicorn observability.main:app --host 0.0.0.0 --port 9090
"""

from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from starlette.responses import Response

from observability.collectors.pipeline_collector import PipelineCollector
from observability.health import build_health_report
from shared.logger import get_logger
from shared.mongo_client import MongoClient
from shared.redis_bus import RedisBus
from shared.heartbeat import heartbeat_loop

logger = get_logger("observability.main")

COLLECT_INTERVAL_S = int(os.getenv("OBSERVABILITY_COLLECT_INTERVAL_S", "30"))
PORT = int(os.getenv("OBSERVABILITY_PORT", "9090"))

_redis: RedisBus | None = None
_mongo: MongoClient | None = None
_collect_task: asyncio.Task | None = None
_hb_task: asyncio.Task | None = None


async def _collect_loop() -> None:
    assert _redis is not None and _mongo is not None
    pc = PipelineCollector(_redis, _mongo)
    while True:
        try:
            await pc.collect()
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.warning("pipeline collect: %s", e)
        await asyncio.sleep(COLLECT_INTERVAL_S)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _redis, _mongo, _collect_task, _hb_task
    _redis = RedisBus()
    _mongo = MongoClient()
    await _redis.connect()
    await _mongo.connect()
    _collect_task = asyncio.create_task(_collect_loop(), name="observability-collect")
    _hb_task = asyncio.create_task(heartbeat_loop(_redis, "observability"), name="observability-hb")
    logger.info("Observability listo (collect cada %ss)", COLLECT_INTERVAL_S)
    yield
    for t in (_collect_task, _hb_task):
        if t:
            t.cancel()
            try:
                await t
            except asyncio.CancelledError:
                pass
    if _redis:
        await _redis.disconnect()
    if _mongo:
        await _mongo.disconnect()
    _collect_task = None
    _hb_task = None
    logger.info("Observability apagado.")


app = FastAPI(title="NYXAR Observability", lifespan=lifespan)


@app.get("/metrics")
async def metrics_endpoint():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/health")
async def health_endpoint():
    if _redis is None or _mongo is None:
        return JSONResponse(status_code=503, content={"status": "starting"})
    report = await build_health_report(_redis, _mongo)
    code = 200 if report.get("status") == "ok" else 503
    return JSONResponse(status_code=code, content=report)
