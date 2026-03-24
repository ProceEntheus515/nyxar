from typing import Optional
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse

from api.auth.deps import require_viewer
from api.validators import (
    validate_event_id_param,
    validate_iso_timestamp_bound,
    validate_mongodb_query,
)
from shared.mongo_client import MongoClient
from api.utils import success_response, error_response
from api.middleware.rate_limit import limiter

router = APIRouter(prefix="/events", tags=["events"], dependencies=[Depends(require_viewer)])
mongo_client = MongoClient()

@router.get("/stats")
async def get_stats():
    hoy = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    col = mongo_client.db.events
    
    # Total de eventos hoy
    total_hoy = await col.count_documents({"timestamp": {"$gte": hoy.isoformat()}})
    
    # Si las fechas en mongodb son strings (isoformat):
    # Tendríamos que parsear o depender de match lógicos. Usaremos find string based match 
    # asumiendo que el timestamp >= hoy strings funciona ISO
    
    # Gte hoy (Formato String ISO Compatible)
    q_hoy = {"timestamp": {"$gte": hoy.strftime("%Y-%m-%dT%H:%M:%S")}}
    total_hoy = await col.count_documents(q_hoy)
    
    # Por fuente (aggregate)
    pipeline_src = [{"$match": q_hoy}, {"$group": {"_id": "$source", "count": {"$sum": 1}}}]
    cursor_src = col.aggregate(pipeline_src)
    por_fuente = {doc["_id"]: doc["count"] async for doc in cursor_src}
    
    # Por reputacion/severidad
    pipeline_sev = [{"$match": q_hoy}, {"$group": {"_id": "$enrichment.reputacion", "count": {"$sum": 1}}}]
    cursor_sev = col.aggregate(pipeline_sev)
    por_reputacion = {doc["_id"] or "N/A": doc["count"] async for doc in cursor_sev}
    
    # Top 10 dominios maliciosos
    pipeline_top = [
        {"$match": {"enrichment.reputacion": "malicioso", "externo.tipo": "dominio"}},
        {"$group": {"_id": "$externo.valor", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 10}
    ]
    cursor_top = col.aggregate(pipeline_top)
    top_10 = [{"dominio": doc["_id"], "count": doc["count"]} async for doc in cursor_top]
    
    data = {
        "total_hoy": total_hoy,
        "por_fuente": por_fuente,
        "por_reputacion": por_reputacion,
        "top_dominios_maliciosos": top_10
    }
    return success_response(data)

@router.get("/{event_id}")
async def get_event(event_id: str):
    try:
        validate_event_id_param(event_id)
    except ValueError as e:
        return JSONResponse(
            status_code=400,
            content=error_response(str(e), "INVALID_EVENT_ID"),
        )
    doc = await mongo_client.db.events.find_one({"id": event_id})
    if not doc:
        return JSONResponse(status_code=404, content=error_response("Evento no encontrado", "EVENT_NOT_FOUND"))
    doc.pop("_id", None)
    return success_response(doc)

@router.get("/")
@limiter.limit("300/minute", override_defaults=False)
async def list_events(
    request: Request,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0, le=10000),
    source: Optional[str] = Query(
        None,
        pattern="^(dns|proxy|firewall|wazuh|endpoint)$",
    ),
    desde: Optional[str] = None,
    hasta: Optional[str] = None,
):
    try:
        desde = validate_iso_timestamp_bound(desde)
        hasta = validate_iso_timestamp_bound(hasta)
    except ValueError as e:
        return JSONResponse(
            status_code=400,
            content=error_response(str(e), "VALIDATION_ERROR"),
        )

    query: dict = {}
    if source:
        query["source"] = source

    date_filter = {}
    if desde:
        date_filter["$gte"] = desde
    if hasta:
        date_filter["$lte"] = hasta
    if date_filter:
        query["timestamp"] = date_filter

    try:
        validate_mongodb_query(query)
    except ValueError as e:
        return JSONResponse(
            status_code=400,
            content=error_response(str(e), "VALIDATION_ERROR"),
        )

    col = mongo_client.db.events
    total = await col.count_documents(query)
    
    cursor = col.find(query).sort("timestamp", -1).skip(offset).limit(limit)
    eventos = []
    async for doc in cursor:
        doc.pop("_id", None)
        eventos.append(doc)
        
    return success_response(eventos, total)
