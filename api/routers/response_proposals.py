"""
Alias /api/v1/response-proposals/* hacia la logica de api.routers.response.
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from api.auth.deps import require_operator, require_viewer
from api.routers import response as response_mod
from api.utils import success_response

router = APIRouter(prefix="/response-proposals", tags=["response-proposals"])


class ApproveBody(BaseModel):
    aprobado_by: Optional[str] = None
    comentario: str = ""


class RejectBody(BaseModel):
    comentario: str
    rechazado_by: Optional[str] = None


@router.get("/", dependencies=[Depends(require_viewer)])
async def list_response_proposals(
    estado: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    items, total = await response_mod._list_proposals_core(estado, limit, offset)
    return success_response(items, total)


@router.post("/{proposal_id}/approve", dependencies=[Depends(require_operator)])
async def approve_response_proposal(
    proposal_id: str,
    body: ApproveBody = ApproveBody(),
):
    return await response_mod.approve_proposal(
        proposal_id,
        response_mod.ApproveBody(
            aprobado_by=body.aprobado_by,
            comentario=body.comentario,
        ),
    )


@router.post("/{proposal_id}/reject", dependencies=[Depends(require_operator)])
async def reject_response_proposal(proposal_id: str, body: RejectBody):
    motivo = body.comentario
    return await response_mod.reject_proposal(
        proposal_id,
        response_mod.RejectBody(motivo=motivo, rechazado_by=body.rechazado_by),
    )
