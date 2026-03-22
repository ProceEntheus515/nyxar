"""
Health checks agregados (sin PII). HealthChecker para /health/detail y WebSocket.
"""

from __future__ import annotations

import asyncio
import os
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Literal, Optional

import httpx
from pydantic import BaseModel, Field

from shared.logger import get_logger
from shared.mongo_client import MongoClient
from shared.redis_bus import RedisBus

logger = get_logger("observability.health")

CHECK_TIMEOUT_S = 2.5

EstadoComponente = Literal["ok", "warning", "critical", "unknown"]
EstadoGeneral = Literal["ok", "degradado", "critico"]


class ComponentHealth(BaseModel):
    nombre: str
    estado: EstadoComponente
    latencia_ms: Optional[float] = None
    mensaje: str
    detalles: dict[str, Any] = Field(default_factory=dict)
    checked_at: datetime


class HealthReport(BaseModel):
    estado_general: EstadoGeneral
    componentes: dict[str, ComponentHealth]
    servicios: dict[str, ComponentHealth]
    apis: dict[str, ComponentHealth]
    resumen: str
    generated_at: datetime


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_iso_ts(raw: Any) -> Optional[datetime]:
    if raw is None:
        return None
    if isinstance(raw, datetime):
        return raw if raw.tzinfo else raw.replace(tzinfo=timezone.utc)
    s = str(raw).strip()
    if not s:
        return None
    try:
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        return datetime.fromisoformat(s)
    except ValueError:
        return None


def _estado_general_de_partes(
    componentes: dict[str, ComponentHealth],
    servicios: dict[str, ComponentHealth],
    apis: dict[str, ComponentHealth],
) -> tuple[EstadoGeneral, str]:
    all_h = list(componentes.values()) + list(servicios.values()) + list(apis.values())
    if any(h.estado == "critical" for h in all_h):
        return "critico", "Al menos un componente en estado crítico."
    if any(h.estado == "warning" for h in all_h):
        return "degradado", "Hay advertencias en uno o más componentes."
    if any(h.estado == "unknown" for h in all_h):
        return "degradado", "Hay componentes sin verificar o no configurados."
    return "ok", "Todos los chequeos obligatorios pasaron."


async def _with_timeout(coro, label: str) -> Any:
    try:
        return await asyncio.wait_for(coro, timeout=CHECK_TIMEOUT_S)
    except asyncio.TimeoutError:
        logger.warning("health timeout: %s", label)
        return None
    except Exception as e:
        logger.warning("health error %s: %s", label, e)
        return None


def _abuse_key() -> str:
    return (os.getenv("ABUSEIPDB_API_KEY") or os.getenv("ABUSEIPDB_KEY") or "").strip()


def _otx_key() -> str:
    return (os.getenv("OTX_API_KEY") or os.getenv("OTX_KEY") or "").strip()


class HealthChecker:
    """Verifica Redis, Mongo, pipeline, heartbeats y APIs externas configuradas."""

    def __init__(self, redis_bus: RedisBus, mongo: MongoClient) -> None:
        self._redis = redis_bus
        self._mongo = mongo

    async def check_redis(self) -> ComponentHealth:
        t0 = time.perf_counter()
        checked = _now()
        detalles: dict[str, Any] = {}
        try:
            if not self._redis.client:
                await self._redis.connect()
            ok = bool(await self._redis.client.ping())
            ms = (time.perf_counter() - t0) * 1000
            if not ok:
                return ComponentHealth(
                    nombre="Redis",
                    estado="critical",
                    latencia_ms=round(ms, 2),
                    mensaje="PING falló",
                    detalles=detalles,
                    checked_at=checked,
                )
            info = await self._redis.client.info("memory")
            clients = await self._redis.client.info("clients")
            detalles["used_memory_human"] = info.get("used_memory_human", "")
            detalles["connected_clients"] = clients.get("connected_clients", 0)
            return ComponentHealth(
                nombre="Redis",
                estado="ok",
                latencia_ms=round(ms, 2),
                mensaje="Operativo",
                detalles=detalles,
                checked_at=checked,
            )
        except Exception as e:
            ms = (time.perf_counter() - t0) * 1000
            return ComponentHealth(
                nombre="Redis",
                estado="critical",
                latencia_ms=round(ms, 2),
                mensaje=str(e)[:200],
                detalles=detalles,
                checked_at=checked,
            )

    async def check_mongodb(self) -> ComponentHealth:
        t0 = time.perf_counter()
        checked = _now()
        detalles: dict[str, Any] = {}
        try:
            if self._mongo.db is None:
                await self._mongo.connect()
            ok = await self._mongo.ping()
            ms_query_start = time.perf_counter()
            start_day = _now().replace(hour=0, minute=0, second=0, microsecond=0)
            events_hoy = await self._mongo.db.events.count_documents(
                {"timestamp": {"$gte": start_day.isoformat()}}
            )
            query_ms = (time.perf_counter() - ms_query_start) * 1000
            ms = (time.perf_counter() - t0) * 1000
            detalles["events_docs_hoy"] = events_hoy
            detalles["query_simple_ms"] = round(query_ms, 2)
            try:
                st = await self._mongo.db.command("dbStats")
                detalles["data_size_bytes"] = int(st.get("dataSize", 0) + st.get("indexSize", 0))
            except Exception:
                pass
            if not ok:
                return ComponentHealth(
                    nombre="MongoDB",
                    estado="critical",
                    latencia_ms=round(ms, 2),
                    mensaje="Ping administrativo falló",
                    detalles=detalles,
                    checked_at=checked,
                )
            return ComponentHealth(
                nombre="MongoDB",
                estado="ok",
                latencia_ms=round(ms, 2),
                mensaje="Operativo",
                detalles=detalles,
                checked_at=checked,
            )
        except Exception as e:
            ms = (time.perf_counter() - t0) * 1000
            return ComponentHealth(
                nombre="MongoDB",
                estado="critical",
                latencia_ms=round(ms, 2),
                mensaje=str(e)[:200],
                detalles=detalles,
                checked_at=checked,
            )

    async def check_pipeline(self) -> ComponentHealth:
        checked = _now()
        try:
            if not self._redis.client:
                await self._redis.connect()
            if self._mongo.db is None:
                await self._mongo.connect()
            raw_pl = await self._redis.stream_latest_payload(self._redis.STREAM_RAW)
            ts_redis = _parse_iso_ts(raw_pl.get("timestamp") if raw_pl else None)
            doc = await self._mongo.db.events.find_one(sort=[("timestamp", -1)])
            ts_mongo = _parse_iso_ts(doc.get("timestamp") if doc else None)
            candidates = [t for t in (ts_redis, ts_mongo) if t is not None]
            if not candidates:
                return ComponentHealth(
                    nombre="Pipeline",
                    estado="critical",
                    latencia_ms=None,
                    mensaje="Sin eventos recientes en Redis ni MongoDB",
                    detalles={"ultimo_stream_raw": None, "ultimo_mongo": None},
                    checked_at=checked,
                )
            latest = max(candidates)
            age = (_now() - latest).total_seconds()
            detalles = {
                "ultimo_evento_utc": latest.isoformat(),
                "segundos_desde_ultimo": int(age),
            }
            if age > 1800:
                return ComponentHealth(
                    nombre="Pipeline",
                    estado="critical",
                    latencia_ms=None,
                    mensaje="Sin eventos nuevos en más de 30 minutos",
                    detalles=detalles,
                    checked_at=checked,
                )
            if age > 600:
                return ComponentHealth(
                    nombre="Pipeline",
                    estado="warning",
                    latencia_ms=None,
                    mensaje="Último evento hace más de 10 minutos",
                    detalles=detalles,
                    checked_at=checked,
                )
            return ComponentHealth(
                nombre="Pipeline",
                estado="ok",
                latencia_ms=None,
                mensaje="Flujo reciente",
                detalles=detalles,
                checked_at=checked,
            )
        except Exception as e:
            return ComponentHealth(
                nombre="Pipeline",
                estado="unknown",
                latencia_ms=None,
                mensaje=str(e)[:200],
                detalles={},
                checked_at=checked,
            )

    async def _heartbeat_component(self, nombre: str, extra: dict[str, Any] | None = None) -> ComponentHealth:
        checked = _now()
        extra = extra or {}
        try:
            if not self._redis.client:
                await self._redis.connect()
            ok = await self._redis.cache_exists(f"heartbeat:{nombre}")
            if ok:
                return ComponentHealth(
                    nombre=nombre,
                    estado="ok",
                    latencia_ms=None,
                    mensaje="Heartbeat activo",
                    detalles=extra,
                    checked_at=checked,
                )
            return ComponentHealth(
                nombre=nombre,
                estado="critical",
                latencia_ms=None,
                mensaje="Sin heartbeat (TTL vencido o servicio caído)",
                detalles=extra,
                checked_at=checked,
            )
        except Exception as e:
            return ComponentHealth(
                nombre=nombre,
                estado="unknown",
                latencia_ms=None,
                mensaje=str(e)[:120],
                detalles=extra,
                checked_at=checked,
            )

    async def check_services(self) -> dict[str, ComponentHealth]:
        out: dict[str, ComponentHealth] = {}
        if self._mongo.db is None:
            await self._mongo.connect()
        start_day = _now().replace(hour=0, minute=0, second=0, microsecond=0)
        start_iso = start_day.isoformat()

        stats_enricher: dict[str, Any] = {}
        try:
            raw = await self._redis.cache_get("enricher:cache_stats")
            if raw and isinstance(raw.get("hit_rate"), (int, float)):
                stats_enricher["cache_hit_rate"] = float(raw["hit_rate"])
        except Exception:
            pass
        inc_hoy = await self._mongo.db.incidents.count_documents({"timestamp": {"$gte": start_iso}})
        ai_hoy = await self._mongo.db.ai_memos.count_documents({"created_at": {"$gte": start_iso}})
        notif_hoy = 0
        try:
            notif_hoy = await self._mongo.db.notifications_log.count_documents({"ts": {"$gte": start_iso}})
        except Exception:
            pass

        out["collector"] = await self._heartbeat_component("collector")
        out["enricher"] = await self._heartbeat_component("enricher", stats_enricher)
        out["correlator"] = await self._heartbeat_component("correlator", {"incidentes_detectados_hoy": inc_hoy})
        out["ai_analyst"] = await self._heartbeat_component("ai_analyst", {"memos_ia_hoy": ai_hoy})
        out["notifier"] = await self._heartbeat_component("notifier", {"notificaciones_enviadas_hoy": notif_hoy})
        out["api"] = await self._heartbeat_component("api")
        return out

    async def check_apis(self) -> dict[str, ComponentHealth]:
        out: dict[str, ComponentHealth] = {}
        out["abuseipdb"] = await self._check_abuseipdb()
        out["otx"] = await self._check_otx()
        out["anthropic"] = await self._check_anthropic()
        out["misp"] = await self._check_misp()
        return out

    async def _check_abuseipdb(self) -> ComponentHealth:
        checked = _now()
        key = _abuse_key()
        if not key:
            return ComponentHealth(
                nombre="AbuseIPDB",
                estado="unknown",
                mensaje="API no configurada",
                detalles={},
                checked_at=checked,
            )
        t0 = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                r = await client.get(
                    "https://api.abuseipdb.com/api/v2/check",
                    params={"ipAddress": "8.8.8.8", "maxAgeInDays": "90"},
                    headers={"Key": key, "Accept": "application/json"},
                )
            ms = (time.perf_counter() - t0) * 1000
            if r.status_code == 200:
                return ComponentHealth(
                    nombre="AbuseIPDB",
                    estado="ok",
                    latencia_ms=round(ms, 2),
                    mensaje="Disponible",
                    detalles={"http_status": r.status_code},
                    checked_at=checked,
                )
            if r.status_code in (401, 403):
                return ComponentHealth(
                    nombre="AbuseIPDB",
                    estado="critical",
                    latencia_ms=round(ms, 2),
                    mensaje="Credenciales rechazadas",
                    detalles={"http_status": r.status_code},
                    checked_at=checked,
                )
            return ComponentHealth(
                nombre="AbuseIPDB",
                estado="warning",
                latencia_ms=round(ms, 2),
                mensaje=f"HTTP {r.status_code}",
                detalles={"http_status": r.status_code},
                checked_at=checked,
            )
        except Exception as e:
            ms = (time.perf_counter() - t0) * 1000
            return ComponentHealth(
                nombre="AbuseIPDB",
                estado="critical",
                latencia_ms=round(ms, 2),
                mensaje=str(e)[:120],
                detalles={},
                checked_at=checked,
            )

    async def _check_otx(self) -> ComponentHealth:
        checked = _now()
        key = _otx_key()
        if not key:
            return ComponentHealth(
                nombre="OTX",
                estado="unknown",
                mensaje="API no configurada",
                detalles={},
                checked_at=checked,
            )
        t0 = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                r = await client.get(
                    "https://otx.alienvault.com/api/v1/user/me",
                    headers={"X-OTX-API-KEY": key, "Accept": "application/json"},
                )
            ms = (time.perf_counter() - t0) * 1000
            if r.status_code == 200:
                return ComponentHealth(
                    nombre="OTX",
                    estado="ok",
                    latencia_ms=round(ms, 2),
                    mensaje="Autenticación válida",
                    detalles={"http_status": r.status_code},
                    checked_at=checked,
                )
            if r.status_code in (401, 403):
                return ComponentHealth(
                    nombre="OTX",
                    estado="critical",
                    latencia_ms=round(ms, 2),
                    mensaje="API key inválida",
                    detalles={"http_status": r.status_code},
                    checked_at=checked,
                )
            return ComponentHealth(
                nombre="OTX",
                estado="warning",
                latencia_ms=round(ms, 2),
                mensaje=f"HTTP {r.status_code}",
                detalles={"http_status": r.status_code},
                checked_at=checked,
            )
        except Exception as e:
            ms = (time.perf_counter() - t0) * 1000
            return ComponentHealth(
                nombre="OTX",
                estado="critical",
                latencia_ms=round(ms, 2),
                mensaje=str(e)[:120],
                detalles={},
                checked_at=checked,
            )

    async def _check_anthropic(self) -> ComponentHealth:
        checked = _now()
        key = (os.getenv("ANTHROPIC_API_KEY") or "").strip()
        if not key:
            return ComponentHealth(
                nombre="Claude API",
                estado="unknown",
                mensaje="API no configurada",
                detalles={},
                checked_at=checked,
            )
        t0 = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                r = await client.get(
                    "https://api.anthropic.com/v1/models",
                    headers={
                        "x-api-key": key,
                        "anthropic-version": "2023-06-01",
                        "Accept": "application/json",
                    },
                )
            ms = (time.perf_counter() - t0) * 1000
            if r.status_code == 200:
                return ComponentHealth(
                    nombre="Claude API",
                    estado="ok",
                    latencia_ms=round(ms, 2),
                    mensaje="Clave aceptada (listado de modelos)",
                    detalles={"http_status": r.status_code},
                    checked_at=checked,
                )
            if r.status_code in (401, 403):
                return ComponentHealth(
                    nombre="Claude API",
                    estado="critical",
                    latencia_ms=round(ms, 2),
                    mensaje="API key inválida",
                    detalles={"http_status": r.status_code},
                    checked_at=checked,
                )
            return ComponentHealth(
                nombre="Claude API",
                estado="warning",
                latencia_ms=round(ms, 2),
                mensaje=f"HTTP {r.status_code}",
                detalles={"http_status": r.status_code},
                checked_at=checked,
            )
        except Exception as e:
            ms = (time.perf_counter() - t0) * 1000
            return ComponentHealth(
                nombre="Claude API",
                estado="critical",
                latencia_ms=round(ms, 2),
                mensaje=str(e)[:120],
                detalles={},
                checked_at=checked,
            )

    async def _check_misp(self) -> ComponentHealth:
        checked = _now()
        base = (os.getenv("MISP_URL") or "").strip().rstrip("/")
        key = (os.getenv("MISP_API_KEY") or "").strip()
        if not base or not key:
            return ComponentHealth(
                nombre="MISP",
                estado="unknown",
                mensaje="MISP no configurado",
                detalles={},
                checked_at=checked,
            )
        t0 = time.perf_counter()
        url = f"{base}/servers/getVersion.json"
        try:
            async with httpx.AsyncClient(timeout=2.0, verify=os.getenv("MISP_VERIFY_SSL", "true").lower() == "true") as client:
                r = await client.get(
                    url,
                    headers={"Authorization": key, "Accept": "application/json"},
                )
            ms = (time.perf_counter() - t0) * 1000
            if r.status_code == 200:
                return ComponentHealth(
                    nombre="MISP",
                    estado="ok",
                    latencia_ms=round(ms, 2),
                    mensaje="Instancia responde",
                    detalles={"http_status": r.status_code},
                    checked_at=checked,
                )
            if r.status_code in (401, 403):
                return ComponentHealth(
                    nombre="MISP",
                    estado="critical",
                    latencia_ms=round(ms, 2),
                    mensaje="Autenticación rechazada",
                    detalles={"http_status": r.status_code},
                    checked_at=checked,
                )
            return ComponentHealth(
                nombre="MISP",
                estado="warning",
                latencia_ms=round(ms, 2),
                mensaje=f"HTTP {r.status_code}",
                detalles={"http_status": r.status_code},
                checked_at=checked,
            )
        except Exception as e:
            ms = (time.perf_counter() - t0) * 1000
            return ComponentHealth(
                nombre="MISP",
                estado="critical",
                latencia_ms=round(ms, 2),
                mensaje=str(e)[:120],
                detalles={},
                checked_at=checked,
            )

    async def full_check(self) -> HealthReport:
        redis_t = asyncio.create_task(_with_timeout(self.check_redis(), "redis"))
        mongo_t = asyncio.create_task(_with_timeout(self.check_mongodb(), "mongo"))
        pipe_t = asyncio.create_task(_with_timeout(self.check_pipeline(), "pipeline"))
        svc_t = asyncio.create_task(_with_timeout(self.check_services(), "services"))
        api_t = asyncio.create_task(_with_timeout(self.check_apis(), "apis"))

        redis_h, mongo_h, pipe_h, svc_d, api_d = await asyncio.gather(
            redis_t, mongo_t, pipe_t, svc_t, api_t
        )

        componentes: dict[str, ComponentHealth] = {}
        if isinstance(redis_h, ComponentHealth):
            componentes["redis"] = redis_h
        else:
            componentes["redis"] = ComponentHealth(
                nombre="Redis",
                estado="unknown",
                mensaje="Timeout o error en chequeo",
                checked_at=_now(),
            )
        if isinstance(mongo_h, ComponentHealth):
            componentes["mongodb"] = mongo_h
        else:
            componentes["mongodb"] = ComponentHealth(
                nombre="MongoDB",
                estado="unknown",
                mensaje="Timeout o error en chequeo",
                checked_at=_now(),
            )
        if isinstance(pipe_h, ComponentHealth):
            componentes["pipeline"] = pipe_h
        else:
            componentes["pipeline"] = ComponentHealth(
                nombre="Pipeline",
                estado="unknown",
                mensaje="Timeout o error en chequeo",
                checked_at=_now(),
            )

        servicios: dict[str, ComponentHealth] = svc_d if isinstance(svc_d, dict) else {}
        apis: dict[str, ComponentHealth] = api_d if isinstance(api_d, dict) else {}

        if not servicios:
            servicios["collector"] = ComponentHealth(
                nombre="collector",
                estado="unknown",
                mensaje="Chequeo de servicios no disponible",
                checked_at=_now(),
            )
        if not apis:
            apis["abuseipdb"] = ComponentHealth(
                nombre="AbuseIPDB",
                estado="unknown",
                mensaje="Chequeo de APIs no disponible",
                checked_at=_now(),
            )

        gen, resumen = _estado_general_de_partes(componentes, servicios, apis)
        return HealthReport(
            estado_general=gen,
            componentes=componentes,
            servicios=servicios,
            apis=apis,
            resumen=resumen,
            generated_at=_now(),
        )


async def quick_health(redis_bus: RedisBus, mongo: MongoClient) -> dict[str, Any]:
    """Respuesta mínima para GET /health (< ~100ms objetivo). Sin detalles sensibles."""
    checker = HealthChecker(redis_bus, mongo)
    r_task = asyncio.create_task(_with_timeout(checker.check_redis(), "q_redis"))
    m_task = asyncio.create_task(_with_timeout(checker.check_mongodb(), "q_mongo"))
    rh, mh = await asyncio.gather(r_task, m_task)
    r_ok = isinstance(rh, ComponentHealth) and rh.estado == "ok"
    m_ok = isinstance(mh, ComponentHealth) and mh.estado == "ok"
    if r_ok and m_ok:
        status: EstadoGeneral = "ok"
    elif not r_ok and not m_ok:
        status = "critico"
    else:
        status = "degradado"
    return {
        "status": status,
        "timestamp": _now().isoformat(),
    }


async def build_health_report(redis_bus: RedisBus, mongo: MongoClient) -> dict[str, Any]:
    """Compatibilidad servicio observability: resumen compacto."""
    q = await quick_health(redis_bus, mongo)
    ok = q["status"] == "ok"
    return {
        "status": "ok" if ok else "degraded",
        "timestamp": q["timestamp"],
        "detail_status": q["status"],
    }


async def compute_events_per_minute_series(mongo: MongoClient, minutes: int = 120) -> list[dict[str, Any]]:
    """Serie para gráfico: una entrada por minuto (últimas `minutes` filas)."""
    if mongo.db is None:
        await mongo.connect()
    now = _now().replace(second=0, microsecond=0)
    keys_order: list[str] = []
    for i in range(minutes - 1, -1, -1):
        t = now - timedelta(minutes=i)
        keys_order.append(t.strftime("%Y-%m-%dT%H:%M"))
    since = (now - timedelta(minutes=minutes)).isoformat()
    buckets: dict[str, int] = {k: 0 for k in keys_order}
    try:
        cursor = mongo.db.events.find({"timestamp": {"$gte": since}}, {"timestamp": 1})
        async for doc in cursor:
            ts = doc.get("timestamp")
            if ts is None:
                continue
            if isinstance(ts, datetime):
                t = ts.astimezone(timezone.utc) if ts.tzinfo else ts.replace(tzinfo=timezone.utc)
                key = t.strftime("%Y-%m-%dT%H:%M")
            else:
                s = str(ts)
                key = s[:16] if len(s) >= 16 else s
            if key in buckets:
                buckets[key] += 1
    except Exception as e:
        logger.warning("compute_events_per_minute_series: %s", e)
    return [{"minute": k, "count": buckets[k]} for k in keys_order]
