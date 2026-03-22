"""
Health check agregado (sin exponer PII ni IPs en la respuesta).
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any

from shared.logger import get_logger
from shared.mongo_client import MongoClient
from shared.redis_bus import RedisBus

logger = get_logger("observability.health")


async def check_redis(redis_bus: RedisBus) -> dict[str, Any]:
    t0 = time.perf_counter()
    ok = False
    err = None
    try:
        if not redis_bus.client:
            await redis_bus.connect()
        ok = bool(await redis_bus.client.ping())
    except Exception as e:
        err = str(e)
        logger.warning("health redis: %s", e)
    ms = int((time.perf_counter() - t0) * 1000)
    return {"ok": ok, "latency_ms": ms, "error": err}


async def check_mongo(mongo: MongoClient) -> dict[str, Any]:
    t0 = time.perf_counter()
    ok = False
    err = None
    try:
        if mongo.db is None:
            await mongo.connect()
        ok = await mongo.ping()
    except Exception as e:
        err = str(e)
        logger.warning("health mongo: %s", e)
    ms = int((time.perf_counter() - t0) * 1000)
    return {"ok": ok, "latency_ms": ms, "error": err}


async def build_health_report(redis_bus: RedisBus, mongo: MongoClient) -> dict[str, Any]:
    r = await check_redis(redis_bus)
    m = await check_mongo(mongo)
    overall = r["ok"] and m["ok"]
    return {
        "status": "ok" if overall else "degraded",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "redis": r,
        "mongodb": m,
    }
