import json
from datetime import datetime, timezone, timedelta
from typing import Any

from shared.logger import get_logger
from shared.mongo_client import MongoClient
from shared.redis_bus import RedisBus

from threat_hunting.models import HuntingContext

logger = get_logger("threat_hunting.context")


def _iso_utc(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


async def build_hunting_context(
    mongo: MongoClient | None = None,
    redis_bus: RedisBus | None = None,
) -> HuntingContext:
    """
    Arma el contexto de hunting desde MongoDB (y un resumen MISP vía Redis si existe).
    No lanza si falta data: devuelve estructuras vacías o mensajes neutros.
    """
    mongo = mongo or MongoClient()
    db = mongo.db
    now = datetime.now(timezone.utc)
    desde_24h = _iso_utc(now - timedelta(hours=24))
    desde_7d = _iso_utc(now - timedelta(days=7))

    estadisticas_24h: dict[str, Any] = {
        "ventana": "24h",
        "por_source_tipo": [],
        "eventos_totales_aprox": 0,
        "ips_internas_distintas_aprox": 0,
        "valores_externos_distintos_aprox": 0,
    }

    try:
        pipeline_stats = [
            {"$match": {"timestamp": {"$gte": desde_24h}}},
            {
                "$group": {
                    "_id": {"source": "$source", "tipo": "$tipo"},
                    "count": {"$sum": 1},
                }
            },
        ]
        grupos = await db.events.aggregate(pipeline_stats).to_list(200)
        estadisticas_24h["por_source_tipo"] = [
            {"source": g["_id"].get("source"), "tipo": g["_id"].get("tipo"), "count": g["count"]}
            for g in grupos
        ]
        estadisticas_24h["eventos_totales_aprox"] = sum(g["count"] for g in grupos)
        n_ips = len(
            await db.events.distinct("interno.ip", {"timestamp": {"$gte": desde_24h}})
        )
        n_ext = len(
            await db.events.distinct("externo.valor", {"timestamp": {"$gte": desde_24h}})
        )
        estadisticas_24h["ips_internas_distintas_aprox"] = n_ips
        estadisticas_24h["valores_externos_distintos_aprox"] = n_ext
    except Exception as e:
        logger.warning("build_hunting_context: estadisticas_24h fallo: %s", e)

    incidentes_semana: list[dict[str, Any]] = []
    try:
        cursor = db.incidents.find(
            {"timestamp": {"$gte": desde_7d}},
            {
                "id": 1,
                "timestamp": 1,
                "patron": 1,
                "descripcion": 1,
                "severidad": 1,
                "mitre_technique": 1,
                "host_afectado": 1,
                "estado": 1,
            },
        ).limit(80)
        incidentes_semana = await cursor.to_list(80)
        for inc in incidentes_semana:
            inc.pop("_id", None)
    except Exception as e:
        logger.warning("build_hunting_context: incidentes fallo: %s", e)

    iocs_sin_alerta: list[dict[str, Any]] = []
    try:
        pipeline_ioc = [
            {"$match": {"timestamp": {"$gte": desde_24h}}},
            {
                "$match": {
                    "$or": [
                        {"correlaciones": {"$exists": False}},
                        {"correlaciones": None},
                        {"correlaciones": []},
                    ]
                }
            },
            {
                "$group": {
                    "_id": {"valor": "$externo.valor", "tipo": "$externo.tipo"},
                    "count": {"$sum": 1},
                }
            },
            {"$sort": {"count": -1}},
            {"$limit": 20},
        ]
        raw_iocs = await db.events.aggregate(pipeline_ioc).to_list(20)
        iocs_sin_alerta = [
            {"valor": r["_id"].get("valor"), "tipo": r["_id"].get("tipo"), "frecuencia": r["count"]}
            for r in raw_iocs
            if r["_id"].get("valor")
        ]
    except Exception as e:
        logger.warning("build_hunting_context: iocs_sin_alerta fallo: %s", e)

    identidades_riesgo_suave: list[dict[str, Any]] = []
    try:
        cursor_id = (
            db.identities.find(
                {"risk_score": {"$gte": 15, "$lte": 35}},
                {"id": 1, "risk_score": 1, "area": 1, "hostname": 1},
            )
            .sort("risk_score", -1)
            .limit(40)
        )
        identidades_riesgo_suave = await cursor_id.to_list(40)
        for doc in identidades_riesgo_suave:
            doc.pop("_id", None)
    except Exception as e:
        logger.warning("build_hunting_context: identidades fallo: %s", e)

    threat_intel_resumen = "Sin conector MISP activo en esta corrida o sin hits recientes."
    try:
        bus = redis_bus or RedisBus()
        if bus.client:
            n_misp = await bus.misp_hits_count_24h()
            threat_intel_resumen = (
                f"Hits de enrichment MISP registrados en Redis (ventana 24h): {n_misp}. "
                "Revisar blocklists MISP en el enricher para IOCs conocidos."
            )
    except Exception as e:
        logger.debug("build_hunting_context: redis misp resumen: %s", e)

    return HuntingContext(
        estadisticas_24h=estadisticas_24h,
        incidentes_semana=incidentes_semana,
        threat_intel_resumen=threat_intel_resumen,
        iocs_sin_alerta=iocs_sin_alerta,
        identidades_riesgo_suave=identidades_riesgo_suave,
    )


def hunting_context_to_prompt_chunks(ctx: HuntingContext) -> dict[str, str]:
    """Serializa el contexto a bloques listos para reemplazar placeholders en prompts."""

    return {
        "context": json.dumps(ctx.estadisticas_24h, ensure_ascii=False, indent=2)
        + "\n\nIOC / externo frecuente sin correlación (top):\n"
        + json.dumps(ctx.iocs_sin_alerta, ensure_ascii=False, indent=2)
        + "\n\nIdentidades con risk_score entre 15 y 35 (bajo umbral de alerta típico):\n"
        + json.dumps(ctx.identidades_riesgo_suave, ensure_ascii=False, indent=2),
        "threat_intel": ctx.threat_intel_resumen,
        "recent_incidents": json.dumps(ctx.incidentes_semana, ensure_ascii=False, indent=2),
    }
