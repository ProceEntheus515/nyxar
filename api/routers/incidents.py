from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel
from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from shared.mongo_client import MongoClient
from api.utils import success_response, error_response

router = APIRouter(prefix="/incidents", tags=["incidents"])
mongo_client = MongoClient()

class EstadoUpdate(BaseModel):
    estado: str

@router.get("/")
async def list_incidents(
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    estado: Optional[str] = None,
    severidad: Optional[str] = None
):
    query = {}
    if estado:
        query["estado"] = estado
    if severidad:
        query["severidad"] = severidad
        
    col = mongo_client.db.incidents
    total = await col.count_documents(query)
    
    # Sort timestamp DESC
    cursor = col.find(query).sort("timestamp", -1).skip(offset).limit(limit)
    incidents = []
    async for doc in cursor:
        doc.pop("_id", None)
        incidents.append(doc)
        
    return success_response(incidents, total)

@router.get("/{incident_id}")
async def get_incident(incident_id: str):
    doc = await mongo_client.db.incidents.find_one({"id": incident_id})
    if not doc:
        return JSONResponse(status_code=404, content=error_response("Incidente no encontrado", "NOT_FOUND"))
        
    doc.pop("_id", None)
    
    # Expandir evento original
    evt_id = doc.get("evento_original_id")
    if evt_id:
        original = await mongo_client.db.events.find_one({"id": evt_id})
        if original:
            original.pop("_id", None)
            doc["evento_expandido"] = original
            
    # Traer todos los eventos de la ultima hora alrededor de ese host (contexto expandido)
    ts_str = doc.get("timestamp")
    host = doc.get("host_afectado")
    
    if host and ts_str:
        try:
            ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
            desde = (ts.timestamp() - 3600)
            hasta = (ts.timestamp() + 3600) # En una ventana de ±1h
            
            # Formatos de fecha compatibles con nuestro index
            # En NYXAR asumimos ISO str
            cursor = mongo_client.db.events.find({
                "interno.ip": host
            }).sort("timestamp", -1).limit(20)
            
            ctx_evts = []
            async for ev in cursor:
                ev.pop("_id", None)
                ctx_evts.append(ev)
                
            doc["contexto_eventos"] = ctx_evts
        except Exception:
            pass
            
    return success_response(doc)

@router.post("/{incident_id}/estado")
async def set_incident_estado(incident_id: str, payload: EstadoUpdate):
    estados_validos = ["investigando", "cerrado", "falso_positivo", "abierto"]
    if payload.estado not in estados_validos:
        return JSONResponse(status_code=400, content=error_response("Estado inválido", "BAD_REQUEST"))
        
    res = await mongo_client.db.incidents.update_one(
        {"id": incident_id},
        {"$set": {"estado": payload.estado}}
    )
    
    if res.matched_count == 0:
        return JSONResponse(status_code=404, content=error_response("Incidente no encontrado", "NOT_FOUND"))
        
    return success_response({"id": incident_id, "estado": payload.estado})
