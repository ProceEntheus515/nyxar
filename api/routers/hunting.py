"""
Rutas REST /hunting/* — hipótesis y sesiones de threat hunting (PROMPTS_V2).
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from api.utils import error_response, success_response
from shared.logger import get_logger
from shared.mongo_client import MongoClient
from threat_hunting.hunter import Hunter, SESSIONS_COLLECTION
from threat_hunting.hypothesis_engine import HYPOTHESES_COLLECTION, HypothesisEngine
from threat_hunting.models import hypothesis_from_mongo

logger = get_logger("api.hunting")

router = APIRouter(prefix="/hunting", tags=["hunting"])
mongo_client = MongoClient()


async def ensure_hunting_indexes() -> None:
    """Índices ligeros para listados de hipótesis y sesiones."""
    try:
        hyp = mongo_client.db[HYPOTHESES_COLLECTION]
        await hyp.create_index("id")
        await hyp.create_index([("estado", 1), ("prioridad", -1)])
        sess = mongo_client.db[SESSIONS_COLLECTION]
        await sess.create_index("id")
        await sess.create_index([("inicio", -1)])
    except Exception as e:
        logger.warning("ensure_hunting_indexes: %s", e)


class ManualHypothesisBody(BaseModel):
    descripcion: str = Field(..., min_length=3, max_length=8000)
    hunter: str = Field(default="analista_manual", max_length=200)


@router.get("/hypotheses")
async def list_hypotheses(limit: int = 50, offset: int = 0):
    q = {"estado": {"$in": ["nueva", "investigando", "confirmada"]}}
    col = mongo_client.db[HYPOTHESES_COLLECTION]
    total = await col.count_documents(q)
    cur = (
        col.find(q)
        .sort([("prioridad", -1), ("creada_at", -1)])
        .skip(max(0, offset))
        .limit(min(limit, 200))
    )
    items: list[dict[str, Any]] = []
    async for doc in cur:
        doc.pop("_id", None)
        items.append(doc)
    return success_response(items, total)


@router.post("/hypotheses")
async def create_hypothesis_manual(body: ManualHypothesisBody):
    engine = HypothesisEngine(mongo=mongo_client)
    hyp = await engine.formalize_manual_hypothesis(
        body.descripcion,
        hunter=body.hunter,
    )
    if hyp is None:
        return JSONResponse(
            status_code=400,
            content=error_response(
                "No se pudo formalizar la hipótesis (IA, duplicado o datos inválidos).",
                "HUNT_FORMALIZE_FAILED",
            ),
        )
    return success_response(hyp.model_dump(mode="json"))


@router.post("/hypotheses/{hypothesis_id}/run")
async def run_hunt_for_hypothesis(
    hypothesis_id: str,
    iniciado_by: str = "api_analista",
):
    doc = await mongo_client.db[HYPOTHESES_COLLECTION].find_one({"id": hypothesis_id})
    if not doc:
        return JSONResponse(
            status_code=404,
            content=error_response("Hipótesis no encontrada", "NOT_FOUND"),
        )
    hypothesis = hypothesis_from_mongo(doc)
    iniciado = iniciado_by[:200] if iniciado_by else "api_analista"
    hunter = Hunter(mongo=mongo_client)
    session = await hunter.run_hunt(hypothesis, iniciado_by=iniciado, skip_critical_guard=True)
    return success_response(session.model_dump(mode="json"))


@router.get("/sessions")
async def list_hunt_sessions(estado: Optional[str] = None, limit: int = 20):
    hunter = Hunter(mongo=mongo_client)
    rows = await hunter.get_sessions(estado=estado, limit=limit)
    return success_response(rows, len(rows))


@router.get("/sessions/{session_id}")
async def get_hunt_session(session_id: str):
    hunter = Hunter(mongo=mongo_client)
    sess = await hunter.get_session_by_id(session_id)
    if not sess:
        return JSONResponse(
            status_code=404,
            content=error_response("Sesión no encontrada", "NOT_FOUND"),
        )
    hyp_doc = await mongo_client.db[HYPOTHESES_COLLECTION].find_one({"id": sess.get("hypothesis_id")})
    if hyp_doc:
        hyp_doc.pop("_id", None)
    sess["hypothesis"] = hyp_doc
    return success_response(sess)
