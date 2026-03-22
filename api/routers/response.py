"""
Rutas REST /response/* alineadas a PROMPTS_V2 (aprobaciones y audit log).
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional, Tuple

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel

from api.utils import error_response, success_response
from auto_response.approval import ApprovalManager
from auto_response.audit import AuditLogger, ensure_audit_log_indexes
from auto_response.engine import COL_PROPOSALS, get_response_engine
from shared.logger import get_logger
from shared.mongo_client import MongoClient
from shared.redis_bus import RedisBus

logger = get_logger("api.response")

router = APIRouter(prefix="/response", tags=["response"])
mongo_client = MongoClient()
_redis_singleton: Optional[RedisBus] = None


def _redis() -> RedisBus:
    global _redis_singleton
    if _redis_singleton is None:
        _redis_singleton = RedisBus()
    return _redis_singleton


def _sync_execute() -> bool:
    return os.getenv("APPROVAL_SYNC_EXECUTE", "true").strip().lower() in (
        "1",
        "true",
        "yes",
    )


async def _list_proposals_core(
    estado: Optional[str],
    limit: int,
    offset: int,
) -> Tuple[List[Dict[str, Any]], int]:
    col = mongo_client.db[COL_PROPOSALS]
    query: Dict[str, Any] = {}
    if estado:
        query["estado"] = estado
    total = await col.count_documents(query)
    cursor = col.find(query).sort("creado_at", -1).skip(offset).limit(limit)
    items: List[Dict[str, Any]] = []
    async for doc in cursor:
        doc.pop("_id", None)
        items.append(doc)
    return items, total


class ApproveBody(BaseModel):
    aprobado_by: Optional[str] = None
    comentario: str = ""


class RejectBody(BaseModel):
    motivo: str
    rechazado_by: Optional[str] = None


@router.get("/proposals")
async def list_proposals(
    estado: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    items, total = await _list_proposals_core(estado, limit, offset)
    return success_response(items, total)


@router.get("/proposals/pending")
async def list_pending_proposals():
    am = ApprovalManager(mongo_client, None, AuditLogger(mongo_client))
    items = await am.get_pending()
    return success_response(items, len(items))


@router.get("/proposals/{proposal_id}")
async def get_proposal_detail(proposal_id: str):
    col = mongo_client.db[COL_PROPOSALS]
    doc = await col.find_one({"id": proposal_id})
    if not doc:
        return JSONResponse(
            status_code=404,
            content=error_response("Propuesta no encontrada", "NOT_FOUND"),
        )
    doc.pop("_id", None)
    incident_id = doc.get("incident_id")
    incident = None
    if incident_id:
        incident = await mongo_client.db.incidents.find_one({"id": incident_id})
        if incident:
            incident.pop("_id", None)
    return success_response({"proposal": doc, "incident": incident})


@router.post("/proposals/{proposal_id}/approve")
async def approve_proposal(proposal_id: str, body: ApproveBody = ApproveBody()):
    rb = _redis()
    if rb.client is None:
        try:
            await rb.connect()
        except Exception as e:
            logger.warning("Redis no disponible para approvals:ready: %s", e)
    am = ApprovalManager(mongo_client, rb, AuditLogger(mongo_client))
    by = (body.aprobado_by or "").strip() or "api"
    ok = await am.approve(proposal_id, by, body.comentario or "")
    if not ok:
        return JSONResponse(
            status_code=400,
            content=error_response(
                "No se pudo aprobar (no existe o no esta pendiente)", "INVALID_STATE"
            ),
        )
    out: Dict[str, Any] = {"aprobado": True, "proposal_id": proposal_id}
    if _sync_execute():
        engine = get_response_engine()
        engine.mongo = mongo_client
        exec_out = await engine.execute_approved(proposal_id)
        out["ejecucion"] = exec_out
        if not exec_out.get("exito"):
            code = exec_out.get("code", "EXEC_FAILED")
            status = 404 if code == "NOT_FOUND" else 400
            return JSONResponse(
                status_code=status,
                content=error_response(exec_out.get("detalle", "Error"), str(code)),
            )
    return success_response(out)


@router.post("/proposals/{proposal_id}/reject")
async def reject_proposal(proposal_id: str, body: RejectBody):
    am = ApprovalManager(mongo_client, None, AuditLogger(mongo_client))
    by = (body.rechazado_by or "").strip() or "api"
    ok = await am.reject(proposal_id, by, body.motivo)
    if not ok:
        return JSONResponse(
            status_code=400,
            content=error_response(
                "No se pudo rechazar (no existe o no esta pendiente)", "INVALID_STATE"
            ),
        )
    return success_response({"id": proposal_id, "estado": "rechazado"})


def _parse_audit_dt(q: Optional[str], end_of_day: bool = False) -> Optional[datetime]:
    if not q or not str(q).strip():
        return None
    s = str(q).strip()
    try:
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except ValueError:
        return None


@router.get("/audit/trail/{incident_id}")
async def get_audit_trail_by_incident(incident_id: str):
    al = AuditLogger(mongo_client)
    items = await al.get_audit_trail(incident_id)
    return success_response(items, len(items))


@router.get("/audit")
async def list_audit_log(
    desde: Optional[str] = Query(None),
    hasta: Optional[str] = Query(None),
    playbook: Optional[str] = Query(None),
    actor: Optional[str] = Query(None),
    exitoso: Optional[bool] = Query(None),
    tipo: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    al = AuditLogger(mongo_client)
    d0 = _parse_audit_dt(desde)
    d1 = _parse_audit_dt(hasta)
    items, total = await al.query_audit(
        desde=d0,
        hasta=d1,
        playbook=playbook,
        actor=actor,
        exitoso=exitoso,
        tipo=tipo,
        limit=limit,
        offset=offset,
    )
    return success_response(items, total)


@router.get("/audit/export")
async def export_audit_log(
    desde: str = Query(..., description="ISO 8601"),
    hasta: str = Query(..., description="ISO 8601"),
    formato: Literal["json", "csv"] = Query("json"),
):
    d0 = _parse_audit_dt(desde)
    d1 = _parse_audit_dt(hasta)
    if d0 is None or d1 is None:
        return JSONResponse(
            status_code=400,
            content=error_response("desde/hasta invalidos", "BAD_RANGE"),
        )
    al = AuditLogger(mongo_client)
    raw = await al.export_period(d0, d1, formato=formato)
    media = "application/json" if formato == "json" else "text/csv; charset=utf-8"
    return Response(content=raw, media_type=media)


async def ensure_response_audit_indexes() -> None:
    if mongo_client.db:
        await ensure_audit_log_indexes(mongo_client.db)
