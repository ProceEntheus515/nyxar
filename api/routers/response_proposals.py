from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from api.utils import error_response, success_response
from auto_response.engine import COL_PROPOSALS, get_response_engine
from shared.mongo_client import MongoClient

router = APIRouter(prefix="/response-proposals", tags=["response-proposals"])
mongo_client = MongoClient()


class ApproveBody(BaseModel):
    aprobado_by: Optional[str] = None


class RejectBody(BaseModel):
    comentario: str


@router.get("/")
async def list_response_proposals(
    estado: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    col = mongo_client.db[COL_PROPOSALS]
    query = {}
    if estado:
        query["estado"] = estado
    total = await col.count_documents(query)
    cursor = col.find(query).sort("creado_at", -1).skip(offset).limit(limit)
    items = []
    async for doc in cursor:
        doc.pop("_id", None)
        items.append(doc)
    return success_response(items, total)


@router.post("/{proposal_id}/approve")
async def approve_response_proposal(
    proposal_id: str,
    body: ApproveBody = ApproveBody(),
):
    col = mongo_client.db[COL_PROPOSALS]
    doc = await col.find_one({"id": proposal_id})
    if not doc:
        return JSONResponse(
            status_code=404,
            content=error_response("Propuesta no encontrada", "NOT_FOUND"),
        )
    if doc.get("estado") != "pendiente_aprobacion":
        return JSONResponse(
            status_code=400,
            content=error_response(
                "Solo se aprueban propuestas pendientes", "INVALID_STATE"
            ),
        )
    now = datetime.now(timezone.utc).isoformat()
    by = (body.aprobado_by if body else None) or "api"
    await col.update_one(
        {"id": proposal_id},
        {"$set": {"estado": "aprobado", "aprobado_at": now, "aprobado_by": by}},
    )
    engine = get_response_engine()
    if mongo_client.db is not None:
        engine.mongo = mongo_client
    out = await engine.execute_approved(proposal_id)
    if not out.get("exito"):
        code = out.get("code", "EXEC_FAILED")
        status = 404 if code == "NOT_FOUND" else 400
        return JSONResponse(
            status_code=status,
            content=error_response(out.get("detalle", "Error"), str(code)),
        )
    return success_response(out)


@router.post("/{proposal_id}/reject")
async def reject_response_proposal(proposal_id: str, body: RejectBody):
    col = mongo_client.db[COL_PROPOSALS]
    doc = await col.find_one({"id": proposal_id})
    if not doc:
        return JSONResponse(
            status_code=404,
            content=error_response("Propuesta no encontrada", "NOT_FOUND"),
        )
    if doc.get("estado") != "pendiente_aprobacion":
        return JSONResponse(
            status_code=400,
            content=error_response(
                "Solo se rechazan propuestas pendientes", "INVALID_STATE"
            ),
        )
    await col.update_one(
        {"id": proposal_id},
        {
            "$set": {
                "estado": "rechazado",
                "rechazado_at": datetime.now(timezone.utc).isoformat(),
                "comentario_rechazo": body.comentario,
            }
        },
    )
    return success_response({"id": proposal_id, "estado": "rechazado"})
