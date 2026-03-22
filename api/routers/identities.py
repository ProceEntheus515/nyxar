from typing import Optional, List
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from shared.mongo_client import MongoClient
from api.utils import success_response, error_response

router = APIRouter(prefix="/identities", tags=["identities"])
mongo_client = MongoClient()

@router.get("/")
async def list_identities(
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    area: Optional[str] = None
):
    query = {}
    if area:
        query["area"] = area
        
    col = mongo_client.db.identities
    total = await col.count_documents(query)
    
    cursor = col.find(query).sort("risk_score", -1).skip(offset).limit(limit)
    identities = []
    async for doc in cursor:
        doc.pop("_id", None)
        identities.append(doc)
        
    return success_response(identities, total)

@router.get("/{identidad_id}")
async def get_identity(identidad_id: str):
    col = mongo_client.db.identities
    doc = await col.find_one({"id": identidad_id})
    if not doc:
        return JSONResponse(status_code=404, content=error_response("Identidad no encontrada", "NOT_FOUND"))
        
    doc.pop("_id", None)
    
    # Eventos recientes (ultimas 24h)
    ayer = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    q_evts = {
        "$or": [
            {"interno.ip": doc.get("ip_asociada", "")},
            {"interno.id_usuario": identidad_id}
        ],
        "timestamp": {"$gte": ayer}
    }
    cursor = mongo_client.db.events.find(q_evts).sort("timestamp", -1).limit(50)
    recientes = []
    async for e in cursor:
        e.pop("_id", None)
        recientes.append(e)
        
    doc["eventos_recientes"] = recientes
    return success_response(doc)

@router.get("/{identidad_id}/timeline")
async def identity_timeline(identidad_id: str, limit: int = Query(100, le=500)):
    # Los ultimos 100 eventos ordenados por timestamp
    q_evts = {
        "$or": [
            {"interno.ip": identidad_id},
            {"interno.id_usuario": identidad_id}
        ]
    }
    
    col = mongo_client.db.identities
    doc = await col.find_one({"id": identidad_id})
    if doc and doc.get("ip_asociada"):
        q_evts["$or"].append({"interno.ip": doc["ip_asociada"]})
        
    cursor = mongo_client.db.events.find(q_evts).sort("timestamp", -1).limit(limit)
    eventos = []
    async for e in cursor:
        e.pop("_id", None)
        eventos.append(e)
        
    return success_response(eventos, len(eventos))
