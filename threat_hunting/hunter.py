"""
Ejecuta sesiones de hunting: pipelines Mongo, conclusión vía HypothesisEngine, persistencia.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any

from shared.logger import get_logger
from shared.mongo_client import MongoClient
from shared.redis_bus import RedisBus

from threat_hunting.hypothesis_engine import HYPOTHESES_COLLECTION, HypothesisEngine
from threat_hunting.models import (
    HuntConclusion,
    HuntQueryAudit,
    HuntSession,
    Hypothesis,
    MongoQuery,
)
from threat_hunting.query_builder import QueryBuilder

logger = get_logger("threat_hunting.hunter")

SESSIONS_COLLECTION = "hunt_sessions"

CRITICAL_SEVERITIES = ("CRITICA", "CRÍTICA", "critica")


async def count_open_critical_incidents(mongo: MongoClient) -> int:
    """Incidentes críticos en estado abierto (NYXAR puede usar CRITICA o CRÍTICA)."""
    return await mongo.db.incidents.count_documents(
        {"estado": "abierto", "severidad": {"$in": list(CRITICAL_SEVERITIES)}}
    )


class Hunter:
    """
    Ejecuta queries de hunting sobre MongoDB y compila resultados hacia HuntSession.
    """

    def __init__(
        self,
        mongo: MongoClient | None = None,
        query_builder: QueryBuilder | None = None,
        hypothesis_engine: HypothesisEngine | None = None,
        redis_bus: RedisBus | None = None,
    ):
        self.mongo = mongo or MongoClient()
        self.query_builder = query_builder or QueryBuilder()
        self.hypothesis_engine = hypothesis_engine or HypothesisEngine(mongo=self.mongo)
        self.redis_bus = redis_bus or RedisBus()

    async def run_query(
        self,
        collection: str,
        pipeline: list[dict[str, Any]],
        timeout: int | None = None,
    ) -> tuple[list[dict[str, Any]], str]:
        """
        Ejecuta aggregation con maxTimeMS (prioridad baja en servidor) y tope de filas.
        Retorna (filas, error_o_vacío). En timeout o error, filas vacías y mensaje descriptivo.
        """
        timeout = timeout or QueryBuilder.MAX_QUERY_DURATION_SECONDS
        max_ms = max(1000, int(timeout * 1000))
        cap = QueryBuilder.MAX_RESULTS
        coll = self.mongo.db[collection]

        async def _aggregate() -> list[dict[str, Any]]:
            cursor = coll.aggregate(
                pipeline,
                maxTimeMS=max_ms,
                allowDiskUse=False,
                batchSize=min(500, cap),
            )
            return await cursor.to_list(cap)

        try:
            rows = await asyncio.wait_for(_aggregate(), timeout=timeout + 3.0)
        except asyncio.TimeoutError:
            logger.warning("Hunter.run_query: timeout cliente collection=%s", collection)
            return [], "timeout"
        except Exception as e:
            logger.warning("Hunter.run_query: error collection=%s err=%s", collection, e)
            return [], str(e)[:500]

        for doc in rows:
            doc.pop("_id", None)
        return rows, ""

    async def run_hunt(
        self,
        hypothesis: Hypothesis,
        *,
        iniciado_by: str = "sistema_autonomo",
        skip_critical_guard: bool = False,
    ) -> HuntSession:
        """
        Pipeline completo: build_queries, ejecutar con timeout, conclude_hunt, persistir sesión.
        Si iniciado_by es sistema_autonomo y hay >5 críticos abiertos, no ejecuta (estado error).
        """
        session = HuntSession(hypothesis_id=hypothesis.id, iniciado_by=iniciado_by)

        if iniciado_by == "sistema_autonomo" and not skip_critical_guard:
            crit = await count_open_critical_incidents(self.mongo)
            if crit > 5:
                session.estado = "error"
                session.mensaje_error = (
                    f"Hunting autónomo suspendido: {crit} incidentes críticos abiertos (>5)."
                )
                session.fin = datetime.now(timezone.utc)
                await self._persist_session(session)
                return session

        mongo_queries: list[MongoQuery] = []
        try:
            mongo_queries = await self.query_builder.build_queries(hypothesis)
        except Exception as e:
            logger.error("Hunter.run_hunt: build_queries falló: %s", e)
            session.estado = "error"
            session.mensaje_error = str(e)[:500]
            session.fin = datetime.now(timezone.utc)
            await self._persist_session(session)
            return session

        if not mongo_queries:
            session.estado = "error"
            session.mensaje_error = "No se generaron pipelines válidos para esta hipótesis."
            session.fin = datetime.now(timezone.utc)
            await self._persist_session(session)
            return session

        await self.mongo.db[HYPOTHESES_COLLECTION].update_one(
            {"id": hypothesis.id},
            {"$set": {"estado": "investigando"}},
        )

        resultados_para_llm: list[dict[str, Any]] = []
        timeouts = 0
        errores = 0

        for idx, mq in enumerate(mongo_queries):
            rows, err = await self.run_query(mq.collection, mq.pipeline, QueryBuilder.MAX_QUERY_DURATION_SECONDS)
            audit = HuntQueryAudit(
                collection=mq.collection,
                pipeline=mq.pipeline,
                ok=not err,
                resultado_count=len(rows),
                error_o_timeout=err,
                muestra=rows[:30],
            )
            session.detalle_queries.append(audit)
            session.queries_ejecutadas += 1
            session.resultados_totales += len(rows)

            if err == "timeout":
                timeouts += 1
            elif err:
                errores += 1

            resultados_para_llm.append(
                {
                    "indice": idx,
                    "collection": mq.collection,
                    "total_documentos": len(rows),
                    "muestra": rows[:25],
                    "error": err or None,
                }
            )

        if timeouts == len(mongo_queries) and len(mongo_queries) > 0:
            session.estado = "timeout"
        elif errores == len(mongo_queries) and len(mongo_queries) > 0:
            session.estado = "error"
            session.mensaje_error = "Todas las queries fallaron."
        else:
            session.estado = "completado"

        try:
            conclusion = await self.hypothesis_engine.conclude_hunt(hypothesis, resultados_para_llm)
            session.conclusion = conclusion
        except Exception as e:
            logger.error("Hunter.run_hunt: conclude_hunt falló: %s", e)
            session.mensaje_error = (session.mensaje_error + " " + str(e))[:500].strip()

        session.fin = datetime.now(timezone.utc)

        if session.conclusion and session.conclusion.crear_incidente:
            await self._crear_incidente_desde_hunt(hypothesis, session.conclusion, session.id)

        await self._actualizar_hipotesis_post_hunt(hypothesis.id, session.conclusion)
        await self._persist_session(session)
        return session

    async def _actualizar_hipotesis_post_hunt(
        self, hypothesis_id: str, conclusion: HuntConclusion | None
    ) -> None:
        if not conclusion:
            return
        nuevo = "confirmada" if conclusion.encontrado else "descartada"
        await self.mongo.db[HYPOTHESES_COLLECTION].update_one(
            {"id": hypothesis_id},
            {"$set": {"estado": nuevo}},
        )

    async def _crear_incidente_desde_hunt(
        self,
        hypothesis: Hypothesis,
        conclusion: HuntConclusion,
        session_id: str,
    ) -> None:
        """
        Inserta incidente como en correlator y publica alerta (mismo canal que honeypot/correlator).
        No reemplaza el flujo de aprobación de response; solo crea el registro de incidente.
        """
        inc_id = f"INC-HUNT-{uuid.uuid4().hex[:10].upper()}"
        host = "multiple"
        if conclusion.evidencia:
            for ev in conclusion.evidencia:
                desc = str(ev.get("descripcion", ""))
                if desc and len(desc) < 80:
                    host = desc[:80]
                    break

        sev = "ALTA" if conclusion.confianza == "alta" else "MEDIA"

        inc = {
            "id": inc_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "patron": "THREAT_HUNT",
            "mitre_technique": hypothesis.tecnica_mitre or "T0000",
            "descripcion": f"[HUNT] {hypothesis.titulo}: {conclusion.resumen}"[:4000],
            "severidad": sev,
            "host_afectado": host,
            "evento_original_id": f"hunt_session:{session_id}",
            "detalles": {
                "hypothesis_id": hypothesis.id,
                "hunt_session_id": session_id,
                "iocs_nuevos": conclusion.iocs_nuevos,
                "confianza": conclusion.confianza,
            },
            "estado": "abierto",
        }
        try:
            await self.mongo.db.incidents.insert_one(inc)
        except Exception as e:
            logger.error("Hunter: no se pudo insertar incidente desde hunt: %s", e)
            return

        try:
            r = self.redis_bus.client
            if r:
                await self.redis_bus.publish_alert("alerts", inc)
        except Exception as e:
            logger.warning("Hunter: publish_alert falló: %s", e)

    async def _persist_session(self, session: HuntSession) -> None:
        doc = session.model_dump(mode="json")
        await self.mongo.db[SESSIONS_COLLECTION].insert_one(doc)

    async def get_sessions(
        self,
        estado: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        q: dict[str, Any] = {}
        if estado:
            q["estado"] = estado
        cur = self.mongo.db[SESSIONS_COLLECTION].find(q).sort("inicio", -1).limit(max(1, min(limit, 200)))
        out: list[dict[str, Any]] = []
        async for doc in cur:
            doc.pop("_id", None)
            out.append(doc)
        return out

    async def get_session_by_id(self, session_id: str) -> dict[str, Any] | None:
        doc = await self.mongo.db[SESSIONS_COLLECTION].find_one({"id": session_id})
        if not doc:
            return None
        doc.pop("_id", None)
        return doc
