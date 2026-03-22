"""Motor SOAR: observa incidents, propone planes y ejecuta tras aprobacion."""

from __future__ import annotations

import asyncio
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pymongo import ReturnDocument

from shared.logger import get_logger
from shared.mongo_client import MongoClient
from shared.redis_bus import RedisBus

from auto_response.models import ResponsePlan
from auto_response.playbook_select import (
    build_response_plan,
    is_candidate_incident,
    is_incident_recent,
    normalize_severidad,
)
from auto_response.playbooks import (
    BlockIPPlaybook,
    DisableUserPlaybook,
    NotifyPlaybook,
    QuarantinePlaybook,
)

logger = get_logger("auto_response.engine")

COL_PROPOSALS = "response_proposals"
COL_AUDIT = "auto_response_audit"


class ResponseEngine:
    def __init__(
        self,
        mongo: Optional[MongoClient] = None,
        redis_bus: Optional[RedisBus] = None,
    ) -> None:
        self.mongo = mongo or MongoClient()
        self.redis_bus = redis_bus or RedisBus()
        self._notify = NotifyPlaybook(self.redis_bus)
        self._block = BlockIPPlaybook()
        self._quarantine = QuarantinePlaybook()
        self._disable = DisableUserPlaybook()
        self._running = False

    def _pb_for(self, tipo: str):
        if tipo == "notify_only":
            return self._notify
        if tipo == "block_ip":
            return self._block
        if tipo == "quarantine":
            return self._quarantine
        if tipo == "disable_user":
            return self._disable
        return self._notify

    async def _ensure_indexes(self) -> None:
        db = self.mongo.db
        if not db:
            return
        coll = db[COL_PROPOSALS]
        try:
            await coll.create_index("id", unique=True, name="response_proposals_id_u")
        except Exception as e:
            logger.warning("Indice response_proposals id: %s", e)
        try:
            await coll.create_index(
                [("incident_id", 1), ("estado", 1)],
                name="response_proposals_incident_estado",
            )
        except Exception as e:
            logger.warning("Indice response_proposals compuesto: %s", e)

    @staticmethod
    def evaluate_incident(incident: Dict[str, Any]) -> Optional[ResponsePlan]:
        return build_response_plan(incident)

    async def has_active_proposal(self, incident_id: str) -> bool:
        db = self.mongo.db
        if not db:
            return True
        doc = await db[COL_PROPOSALS].find_one(
            {
                "incident_id": incident_id,
                "estado": {"$in": ["pendiente_aprobacion", "aprobado", "ejecutando"]},
            }
        )
        return doc is not None

    async def propose_actions(
        self,
        incident: Dict[str, Any],
        *,
        force_auto_approve: Optional[bool] = None,
    ) -> Optional[str]:
        incident_id = str(incident.get("id") or "")
        if not incident_id:
            return None
        if await self.has_active_proposal(incident_id):
            return None
        plan = build_response_plan(incident)
        if not plan:
            return None

        proposal_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        auto_crit = force_auto_approve
        if auto_crit is None:
            auto_crit = os.getenv("AUTO_RESPONSE_CRITICO", "").strip().lower() in (
                "1",
                "true",
                "yes",
            )
        auto_aprobado = bool(auto_crit and normalize_severidad(incident) == "CRITICA")

        estado_inicial = "aprobado" if auto_aprobado else "pendiente_aprobacion"
        doc: Dict[str, Any] = {
            "id": proposal_id,
            "incident_id": plan.incident_id,
            "estado": estado_inicial,
            "plan": plan.model_dump(mode="json"),
            "resultados": [],
            "creado_at": now,
            "aprobado_at": now if auto_aprobado else None,
            "aprobado_by": "AUTO_RESPONSE_CRITICO" if auto_aprobado else None,
            "ejecutado_at": None,
        }
        db = self.mongo.db
        if not db:
            return None
        await db[COL_PROPOSALS].insert_one(doc)
        if auto_aprobado:
            await self.execute_approved(proposal_id)
        return proposal_id

    async def execute_approved(self, proposal_id: str) -> Dict[str, Any]:
        db = self.mongo.db
        if not db:
            return {"exito": False, "detalle": "MongoDB no conectado"}

        coll = db[COL_PROPOSALS]
        prev = await coll.find_one_and_update(
            {"id": proposal_id, "estado": "aprobado"},
            {"$set": {"estado": "ejecutando"}},
            return_document=ReturnDocument.BEFORE,
        )
        if not prev:
            cur = await coll.find_one({"id": proposal_id})
            if not cur:
                return {"exito": False, "detalle": "Propuesta no encontrada", "code": "NOT_FOUND"}
            if cur.get("estado") == "ejecutado":
                return {"exito": True, "detalle": "Ya ejecutada"}
            if cur.get("estado") == "ejecutando":
                return {"exito": False, "detalle": "Ejecucion en curso", "code": "IN_PROGRESS"}
            return {
                "exito": False,
                "detalle": f"Estado invalido: {cur.get('estado')}",
                "code": "INVALID_STATE",
            }

        plan_data = prev.get("plan") or {}
        try:
            plan = ResponsePlan(**plan_data)
        except Exception as e:
            await coll.update_one(
                {"id": proposal_id},
                {"$set": {"estado": "error_ejecucion", "error_parseo": str(e)}},
            )
            return {"exito": False, "detalle": f"Plan invalido: {e}", "code": "BAD_PLAN"}

        incident_id = plan.incident_id
        resultados: List[Dict[str, Any]] = []
        ctx: Dict[str, Any] = {"incident_id": incident_id, "proposal_id": proposal_id}

        audit = db[COL_AUDIT]
        try:
            for i, accion in enumerate(plan.acciones):
                if i > 0:
                    await asyncio.sleep(1)
                pb = self._pb_for(accion.tipo)
                try:
                    exec_out = await pb.execute(accion, ctx)
                except Exception as e:
                    exec_out = {
                        "exito": False,
                        "detalle": str(e),
                        "payload_redactado": {},
                    }
                entry = {
                    "tipo": accion.tipo,
                    "objetivo": accion.objetivo,
                    "exito": exec_out.get("exito", False),
                    "detalle": exec_out.get("detalle", ""),
                }
                resultados.append(entry)
                audit_doc = {
                    "ts": datetime.now(timezone.utc).isoformat(),
                    "proposal_id": proposal_id,
                    "incident_id": incident_id,
                    "tipo_accion": accion.tipo,
                    "objetivo": accion.objetivo,
                    "exito": entry["exito"],
                    "detalle": entry["detalle"],
                    "payload_redactado": exec_out.get("payload_redactado") or {},
                }
                await audit.insert_one(audit_doc)
        except Exception as e:
            logger.error("execute_approved fallo: %s", e)
            await coll.update_one(
                {"id": proposal_id},
                {
                    "$set": {
                        "estado": "error_ejecucion",
                        "resultados": resultados,
                        "error_ejecucion": str(e),
                    }
                },
            )
            return {"exito": False, "detalle": str(e), "code": "EXEC_ERROR"}

        done_at = datetime.now(timezone.utc).isoformat()
        await coll.update_one(
            {"id": proposal_id},
            {
                "$set": {
                    "estado": "ejecutado",
                    "ejecutado_at": done_at,
                    "resultados": resultados,
                }
            },
        )
        await db.incidents.update_one(
            {"id": incident_id},
            {"$set": {"estado": "investigando"}},
        )
        return {"exito": True, "detalle": "Ejecutado", "resultados": resultados}

    async def _handle_incident_doc(self, doc: Dict[str, Any]) -> None:
        try:
            if not is_candidate_incident(doc):
                return
            lookback = 7
            try:
                lookback = int(os.getenv("AUTO_RESPONSE_LOOKBACK_DAYS", "7") or "7")
            except ValueError:
                lookback = 7
            if not is_incident_recent(doc, lookback):
                return
            await self.propose_actions(doc)
        except Exception as e:
            logger.error("Error procesando incidente auto_response: %s", e)

    async def _run_change_stream(self) -> None:
        db = self.mongo.db
        if not db:
            raise RuntimeError("Mongo sin db")
        coll = db.incidents
        logger.info("auto_response: Change Stream en incidents")
        stream = coll.watch(full_document="updateLookup")
        try:
            async for change in stream:
                doc = change.get("fullDocument")
                if not isinstance(doc, dict):
                    continue
                asyncio.create_task(self._handle_incident_doc(dict(doc)))
        finally:
            closer = getattr(stream, "close", None)
            if closer is not None:
                res = closer()
                if asyncio.iscoroutine(res):
                    await res

    async def _poll_loop(self) -> None:
        poll_s = 45
        try:
            poll_s = max(15, int(os.getenv("AUTO_RESPONSE_POLL_S", "45") or "45"))
        except ValueError:
            poll_s = 45
        db = self.mongo.db
        if not db:
            return
        coll = db.incidents
        logger.info("auto_response: polling incidents cada %ss", poll_s)
        lookback = 7
        try:
            lookback = int(os.getenv("AUTO_RESPONSE_LOOKBACK_DAYS", "7") or "7")
        except ValueError:
            lookback = 7
        while self._running:
            try:
                query = {
                    "$or": [
                        {"estado": {"$exists": False}},
                        {"estado": None},
                        {"estado": "abierto"},
                    ]
                }
                async for doc in coll.find(query):
                    d = dict(doc)
                    if not is_incident_recent(d, lookback):
                        continue
                    asyncio.create_task(self._handle_incident_doc(d))
            except Exception as e:
                logger.error("auto_response polling error: %s", e)
            await asyncio.sleep(poll_s)

    async def start(self) -> None:
        enabled = os.getenv("AUTO_RESPONSE_ENABLED", "").strip().lower() in (
            "1",
            "true",
            "yes",
        )
        if not enabled:
            logger.info(
                "Motor auto_response deshabilitado (AUTO_RESPONSE_ENABLED distinto de true)"
            )
            return

        await self.mongo.connect()
        use_redis = os.getenv("AUTO_RESPONSE_USE_REDIS", "true").strip().lower() in (
            "1",
            "true",
            "yes",
        )
        if use_redis:
            try:
                await self.redis_bus.connect()
            except Exception as e:
                logger.warning("Redis opcional no disponible para notify: %s", e)

        await self._ensure_indexes()
        self._running = True

        try:
            await self._run_change_stream()
        except Exception as e:
            logger.warning(
                "Change Stream no disponible; polling fallback: %s",
                e,
            )
            await self._poll_loop()


_engine_instance: Optional[ResponseEngine] = None


def get_response_engine() -> ResponseEngine:
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = ResponseEngine()
    return _engine_instance
