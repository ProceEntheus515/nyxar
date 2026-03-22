"""
Flujo de aprobacion/rechazo de propuestas SOAR (PROMPTS_V2).
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from shared.logger import get_logger
from shared.mongo_client import MongoClient
from shared.redis_bus import RedisBus

from auto_response.audit import AuditLogger, build_context_snapshot

# Mismo nombre que COL_PROPOSALS en engine (evita import circular).
COL_RESPONSE_PROPOSALS = "response_proposals"

logger = get_logger("auto_response.approval")

CHANNEL_APPROVALS_READY = "approvals:ready"

URGENCY_RANK = {"inmediata": 3, "proxima_hora": 2, "proximo_dia": 1}


def _parse_creado_at(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return None
        try:
            if s.endswith("Z"):
                s = s[:-1] + "+00:00"
            return datetime.fromisoformat(s)
        except ValueError:
            return None
    return None


def _pending_sort_key(doc: Dict[str, Any]) -> Tuple[int, str]:
    plan = doc.get("plan") or {}
    u = str(plan.get("urgencia") or "proxima_hora")
    rank = URGENCY_RANK.get(u, 0)
    creado = doc.get("creado_at") or ""
    return (-rank, str(creado))


class ApprovalManager:
    def __init__(
        self,
        mongo: MongoClient,
        redis_bus: Optional[RedisBus] = None,
        audit: Optional[AuditLogger] = None,
    ) -> None:
        self.mongo = mongo
        self.redis_bus = redis_bus
        self.audit = audit or AuditLogger(mongo)

    async def approve(
        self,
        proposal_id: str,
        aprobado_by: str,
        comentario: str = "",
    ) -> bool:
        db = self.mongo.db
        if db is None:
            return False
        col = db[COL_RESPONSE_PROPOSALS]
        doc = await col.find_one({"id": proposal_id})
        if not doc or doc.get("estado") != "pendiente_aprobacion":
            return False
        incident_id = str(doc.get("incident_id") or "")
        now = datetime.now(timezone.utc).isoformat()
        res = await col.update_one(
            {"id": proposal_id, "estado": "pendiente_aprobacion"},
            {
                "$set": {
                    "estado": "aprobado",
                    "aprobado_at": now,
                    "aprobado_by": aprobado_by,
                    "comentario_aprobacion": comentario or None,
                }
            },
        )
        if res.modified_count == 0:
            return False
        snap = await build_context_snapshot(db, incident_id)
        plan = doc.get("plan") or {}
        playbook_name = str(plan.get("playbook_nombre") or "response_plan")
        await self.audit.log_action(
            tipo="aprobacion",
            proposal_id=proposal_id,
            actor=aprobado_by,
            incident_id=incident_id,
            playbook=playbook_name,
            objetivo=incident_id,
            detalle={**snap, "comentario": (comentario or "")[:500]},
            exitoso=None,
        )
        if self.redis_bus and getattr(self.redis_bus, "client", None):
            try:
                await self.redis_bus.publish_alert(
                    CHANNEL_APPROVALS_READY,
                    {"proposal_id": proposal_id},
                )
            except Exception as e:
                logger.warning("publish approvals:ready: %s", e)
        return True

    async def reject(
        self,
        proposal_id: str,
        rechazado_by: str,
        motivo: str,
    ) -> bool:
        db = self.mongo.db
        if db is None:
            return False
        col = db[COL_RESPONSE_PROPOSALS]
        doc = await col.find_one({"id": proposal_id})
        if not doc or doc.get("estado") != "pendiente_aprobacion":
            return False
        incident_id = str(doc.get("incident_id") or "")
        now = datetime.now(timezone.utc).isoformat()
        res = await col.update_one(
            {"id": proposal_id, "estado": "pendiente_aprobacion"},
            {
                "$set": {
                    "estado": "rechazado",
                    "rechazado_at": now,
                    "rechazado_by": rechazado_by,
                    "comentario_rechazo": motivo,
                }
            },
        )
        if res.modified_count == 0:
            return False
        snap = await build_context_snapshot(db, incident_id)
        plan = doc.get("plan") or {}
        playbook_name = str(plan.get("playbook_nombre") or "response_plan")
        await self.audit.log_action(
            tipo="rechazo",
            proposal_id=proposal_id,
            actor=rechazado_by,
            incident_id=incident_id,
            playbook=playbook_name,
            objetivo=incident_id,
            detalle={**snap, "motivo": (motivo or "")[:2000]},
            exitoso=False,
        )
        return True

    async def get_pending(self) -> List[Dict[str, Any]]:
        db = self.mongo.db
        if db is None:
            return []
        col = db[COL_RESPONSE_PROPOSALS]
        cursor = col.find({"estado": "pendiente_aprobacion"})
        items: List[Dict[str, Any]] = []
        async for doc in cursor:
            d = dict(doc)
            d.pop("_id", None)
            items.append(d)
        items.sort(key=_pending_sort_key)
        return items

    async def auto_expire(self) -> int:
        db = self.mongo.db
        if db is None:
            return 0
        try:
            hours = float(os.getenv("APPROVAL_TIMEOUT", "24") or "24")
        except ValueError:
            hours = 24.0
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        col = db[COL_RESPONSE_PROPOSALS]
        cursor = col.find({"estado": "pendiente_aprobacion"})
        count = 0
        now_iso = datetime.now(timezone.utc).isoformat()
        async for doc in cursor:
            ts = _parse_creado_at(doc.get("creado_at"))
            if ts is None or ts >= cutoff:
                continue
            pid = doc.get("id")
            if not pid:
                continue
            res = await col.update_one(
                {"id": pid, "estado": "pendiente_aprobacion"},
                {
                    "$set": {
                        "estado": "expirado",
                        "expirado_at": now_iso,
                    }
                },
            )
            if res.modified_count:
                count += 1
                incident_id = str(doc.get("incident_id") or "")
                plan = doc.get("plan") or {}
                playbook_name = str(plan.get("playbook_nombre") or "response_plan")
                snap = await build_context_snapshot(db, incident_id)
                await self.audit.log_action(
                    tipo="expiracion",
                    proposal_id=str(pid),
                    actor="sistema",
                    incident_id=incident_id,
                    playbook=playbook_name,
                    objetivo=incident_id,
                    detalle={
                        **snap,
                        "horas_limite": hours,
                    },
                    exitoso=False,
                )
        return count
