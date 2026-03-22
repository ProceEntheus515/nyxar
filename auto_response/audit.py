"""
Registro append-only de acciones SOAR para auditoria (PROMPTS_V2).
Coleccion audit_log: solo insert_one; write concern majority cuando aplica.
"""

from __future__ import annotations

import csv
import io
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional

from pymongo import WriteConcern
from pymongo.errors import PyMongoError

from shared.logger import get_logger
from shared.mongo_client import MongoClient

logger = get_logger("auto_response.audit")

AUDIT_COLLECTION = "audit_log"


def _safe_payload_fragment(payload: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Copia metadatos seguros del payload de playbook (sin tokens ni secretos)."""
    if not payload:
        return {}
    out: Dict[str, Any] = {}
    for key in (
        "objetivo",
        "execution_id",
        "puede_deshacer",
        "tipo",
    ):
        if key in payload:
            out[key] = payload[key]
    det = payload.get("detalles")
    if isinstance(det, dict):
        out["detalles"] = {
            k: v
            for k, v in det.items()
            if k.lower() not in ("password", "token", "secret", "authorization")
        }
    return out


async def build_context_snapshot(db: Any, incident_id: str) -> Dict[str, Any]:
    """Contexto no sensible para enriquecer detalle de auditoria."""
    snap: Dict[str, Any] = {
        "incident_id": incident_id,
        "hora_utc": datetime.now(timezone.utc).strftime("%H:%M"),
    }
    if not incident_id or db is None:
        return snap
    try:
        inc = await db.incidents.find_one({"id": incident_id})
        if inc:
            snap["severidad_incidente"] = inc.get("severidad")
            host = (inc.get("host_afectado") or "").strip()
            if host:
                ident = await db.identities.find_one({"ip_asociada": host})
                if ident and ident.get("risk_score") is not None:
                    snap["risk_score_identidad"] = ident.get("risk_score")
    except Exception as e:
        logger.warning("build_context_snapshot: %s", e)
    return snap


async def ensure_audit_log_indexes(db: Any) -> None:
    if db is None:
        return
    coll = db[AUDIT_COLLECTION]
    try:
        await coll.create_index(
            [("incident_id", 1), ("timestamp", 1)],
            name="audit_log_incident_ts",
        )
        await coll.create_index("proposal_id", name="audit_log_proposal_id")
        await coll.create_index(
            [("tipo", 1), ("timestamp", 1)],
            name="audit_log_tipo_ts",
        )
    except PyMongoError as e:
        logger.warning("Indices audit_log: %s", e)


class AuditLogger:
    """Append-only audit_log en MongoDB."""

    AUDIT_COLLECTION = AUDIT_COLLECTION

    def __init__(self, mongo: MongoClient) -> None:
        self.mongo = mongo

    def _collection(self) -> Any:
        db = self.mongo.db
        if db is None:
            raise RuntimeError("MongoDB no conectado")
        wc = WriteConcern(w="majority", wtimeout=5000)
        return db.get_collection(AUDIT_COLLECTION, write_concern=wc)

    async def log_action(
        self,
        tipo: str,
        proposal_id: str,
        actor: str,
        incident_id: str,
        playbook: str,
        objetivo: str,
        detalle: Dict[str, Any],
        exitoso: Optional[bool] = None,
        ip_del_actor: Optional[str] = None,
    ) -> str:
        doc: Dict[str, Any] = {
            "audit_entry_id": str(uuid.uuid4()),
            "tipo": tipo,
            "timestamp": datetime.now(timezone.utc),
            "proposal_id": proposal_id or "",
            "actor": actor,
            "incident_id": incident_id or "",
            "playbook": playbook or "",
            "objetivo": objetivo or "",
            "detalle": detalle or {},
            "exitoso": exitoso,
            "ip_del_actor": ip_del_actor,
        }
        try:
            res = await self._collection().insert_one(doc)
            return str(res.inserted_id)
        except Exception as e:
            logger.warning("AuditLogger.insert fallo: %s", e)
            return doc["audit_entry_id"]

    async def get_audit_trail(self, incident_id: str) -> List[Dict[str, Any]]:
        db = self.mongo.db
        if db is None:
            return []
        cursor = db[AUDIT_COLLECTION].find({"incident_id": incident_id}).sort(
            "timestamp", 1
        )
        out: List[Dict[str, Any]] = []
        async for doc in cursor:
            d = dict(doc)
            d["_id"] = str(d.get("_id", ""))
            if isinstance(d.get("timestamp"), datetime):
                d["timestamp"] = d["timestamp"].isoformat()
            out.append(d)
        return out

    async def query_audit(
        self,
        *,
        desde: Optional[datetime] = None,
        hasta: Optional[datetime] = None,
        playbook: Optional[str] = None,
        actor: Optional[str] = None,
        exitoso: Optional[bool] = None,
        tipo: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[List[Dict[str, Any]], int]:
        db = self.mongo.db
        if db is None:
            return [], 0
        q: Dict[str, Any] = {}
        if desde or hasta:
            q["timestamp"] = {}
            if desde:
                q["timestamp"]["$gte"] = desde
            if hasta:
                q["timestamp"]["$lte"] = hasta
        if playbook:
            q["playbook"] = playbook
        if actor:
            q["actor"] = actor
        if exitoso is not None:
            q["exitoso"] = exitoso
        if tipo:
            q["tipo"] = tipo
        coll = db[AUDIT_COLLECTION]
        total = await coll.count_documents(q)
        cursor = (
            coll.find(q).sort("timestamp", -1).skip(offset).limit(min(limit, 500))
        )
        items: List[Dict[str, Any]] = []
        async for doc in cursor:
            d = dict(doc)
            oid = d.pop("_id", None)
            d["_id"] = str(oid) if oid is not None else ""
            if isinstance(d.get("timestamp"), datetime):
                d["timestamp"] = d["timestamp"].isoformat()
            items.append(d)
        return items, total

    async def export_period(
        self,
        desde: datetime,
        hasta: datetime,
        formato: Literal["json", "csv"],
    ) -> bytes:
        db = self.mongo.db
        if db is None:
            return b""
        coll = db[AUDIT_COLLECTION]
        cursor = coll.find(
            {"timestamp": {"$gte": desde, "$lte": hasta}}
        ).sort("timestamp", 1)
        rows: List[Dict[str, Any]] = []
        async for doc in cursor:
            d = dict(doc)
            oid = d.pop("_id", None)
            d["_id"] = str(oid) if oid is not None else ""
            if isinstance(d.get("timestamp"), datetime):
                d["timestamp"] = d["timestamp"].isoformat()
            rows.append(d)
        if formato == "json":
            return json.dumps(rows, ensure_ascii=False, default=str).encode("utf-8")
        buf = io.StringIO()
        fieldnames = [
            "timestamp",
            "tipo",
            "proposal_id",
            "actor",
            "incident_id",
            "playbook",
            "objetivo",
            "exitoso",
        ]
        w = csv.DictWriter(buf, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            line = {k: r.get(k, "") for k in fieldnames}
            w.writerow(line)
        return buf.getvalue().encode("utf-8")
