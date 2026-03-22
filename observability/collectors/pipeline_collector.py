"""
Actualiza Gauges desde Redis/Mongo cada ciclo (ligero; sin exponer datos crudos).
"""

from __future__ import annotations

import time
from typing import Any

from observability import metrics as m
from shared.logger import get_logger
from shared.mongo_client import MongoClient
from shared.redis_bus import RedisBus

logger = get_logger("observability.pipeline_collector")


def _norm_sev_label(raw: str | None) -> str:
    if not raw:
        return "desconocida"
    u = str(raw).upper().replace("Í", "I")
    if "CRIT" in u:
        return "critica"
    if u == "ALTA":
        return "alta"
    if u == "MEDIA":
        return "media"
    if u == "BAJA":
        return "baja"
    return "otra"


class PipelineCollector:
    """
    Consulta Redis streams, heartbeats, blocklists; Mongo incidents e identities.
    """

    def __init__(self, redis_bus: RedisBus, mongo: MongoClient) -> None:
        self._redis = redis_bus
        self._mongo = mongo

    async def check_service_health(self, servicio: str) -> bool:
        if not self._redis.client:
            return False
        try:
            return await self._redis.cache_exists(f"heartbeat:{servicio}")
        except Exception:
            return False

    async def collect(self) -> None:
        await self._collect_streams()
        await self._collect_blocklists()
        await self._collect_heartbeats()
        await self._collect_incidents()
        await self._collect_identities_risk()
        await self._collect_cache_hit_rate()

    async def _time_redis(self, operacion: str, coro) -> Any:
        t0 = time.perf_counter()
        try:
            return await coro
        finally:
            elapsed = time.perf_counter() - t0
            m.REDIS_OPERATION_LATENCY.labels(operacion=operacion).observe(elapsed)

    async def _collect_streams(self) -> None:
        for name, label in (
            (self._redis.STREAM_RAW, "events_raw"),
            (self._redis.STREAM_ENRICHED, "events_enriched"),
            (self._redis.STREAM_ALERTS, "events_alerts"),
        ):
            try:
                n = await self._time_redis("xlen", self._redis.stream_length(name))
                m.EVENTOS_EN_COLA.labels(stream=label).set(n)
            except Exception as e:
                logger.warning("collect stream %s: %s", name, e)

    async def _collect_blocklists(self) -> None:
        for lista in m.BLOCKLIST_LISTAS:
            try:
                n = await self._time_redis(
                    "scard",
                    self._redis.blocklist_size(lista),
                )
                m.BLOCKLIST_SIZES.labels(lista=lista).set(n)
            except Exception as e:
                logger.debug("blocklist %s: %s", lista, e)

    async def _collect_heartbeats(self) -> None:
        for svc in m.SERVICIOS_HEARTBEAT:
            ok = await self.check_service_health(svc)
            m.SERVICIOS_ACTIVOS.labels(servicio=svc).set(1.0 if ok else 0.0)

    async def _collect_incidents(self) -> None:
        t0 = time.perf_counter()
        try:
            if not self._mongo.db:
                await self._mongo.connect()
            col = self._mongo.db.incidents
            pipeline = [
                {
                    "$match": {
                        "$or": [
                            {"estado": {"$exists": False}},
                            {"estado": {"$nin": ["cerrado", "falso_positivo"]}},
                        ]
                    }
                },
                {"$group": {"_id": "$severidad", "count": {"$sum": 1}}},
            ]
            counts: dict[str, int] = {}
            async for row in col.aggregate(pipeline):
                lab = _norm_sev_label(row.get("_id"))
                counts[lab] = counts.get(lab, 0) + int(row.get("count", 0))
            for lab in ("critica", "alta", "media", "baja", "otra", "desconocida"):
                m.INCIDENTES_ACTIVOS.labels(severidad=lab).set(float(counts.get(lab, 0)))
        except Exception as e:
            logger.warning("collect incidents: %s", e)
        finally:
            elapsed = time.perf_counter() - t0
            m.MONGODB_OPERATION_LATENCY.labels(operacion="aggregate", coleccion="incidents").observe(
                elapsed
            )

    async def _collect_identities_risk(self) -> None:
        t0 = time.perf_counter()
        try:
            if not self._mongo.db:
                await self._mongo.connect()
            col = self._mongo.db.identities
            pipeline = [
                {
                    "$group": {
                        "_id": None,
                        "avg": {"$avg": "$risk_score"},
                    }
                }
            ]
            avg_val = 0.0
            async for row in col.aggregate(pipeline):
                v = row.get("avg")
                if v is not None:
                    avg_val = float(v)
                break
            m.IDENTITIES_RISK_AVG.set(avg_val)
        except Exception as e:
            logger.warning("collect identities risk: %s", e)
        finally:
            elapsed = time.perf_counter() - t0
            m.MONGODB_OPERATION_LATENCY.labels(operacion="aggregate", coleccion="identities").observe(
                elapsed
            )

    async def _collect_cache_hit_rate(self) -> None:
        """
        Si en el futuro el enricher publica stats en Redis, leer aquí.
        Por ahora deja 0 si no hay clave.
        """
        try:
            raw = await self._redis.cache_get("enricher:cache_stats")
            if raw and isinstance(raw.get("hit_rate"), (int, float)):
                m.CACHE_HIT_RATE.set(float(raw["hit_rate"]))
            else:
                m.CACHE_HIT_RATE.set(0.0)
        except Exception:
            m.CACHE_HIT_RATE.set(0.0)
