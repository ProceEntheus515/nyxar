from typing import List
from datetime import datetime, timezone
from fastapi import APIRouter

from shared.mongo_client import MongoClient
from api.utils import success_response, error_response

router = APIRouter(prefix="/alerts", tags=["alerts"])
mongo_client = MongoClient()

@router.get("/honeypots")
async def list_honeypot_hits(limit: int = 50, offset: int = 0):
    col = mongo_client.db.honeypot_hits
    total = await col.count_documents({})
    
    cursor = col.find({}).sort("timestamp", -1).skip(offset).limit(limit)
    hits = []
    async for doc in cursor:
        doc.pop("_id", None)
        # Siempre max criticidad
        doc["severidad"] = "CRÍTICA"
        hits.append(doc)
        
    return success_response(hits, total)

@router.get("/summary")
async def alerts_summary():
    hoy = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    db = mongo_client.db
    
    # Incidentes abiertos (asumiendo que los que carecen de 'estado' o no son cerrados)
    abiertos = await db.incidents.count_documents({"estado": {"$nin": ["cerrado", "falso_positivo"]}})
    
    # Críticos (Asumiendo que severidad CRITICA / CRÍTICA)
    criticos = await db.incidents.count_documents({"severidad": {"$in": ["CRITICA", "CRÍTICA"]}})
    
    # Honeypots hoy (String comparison iso)
    honeypots_hoy = await db.honeypot_hits.count_documents({"timestamp": {"$gte": hoy}})
    
    # ID mayor riesgo
    docs = await db.identities.find().sort("risk_score", -1).limit(1).to_list(1)
    top_risk_id = docs[0].get("id") if docs else None
    
    # Dominio malicioso más consultado (via aggregate events)
    pipeline_top = [
        {"$match": {"enrichment.reputacion": "malicioso", "externo.tipo": "dominio"}},
        {"$group": {"_id": "$externo.valor", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 1}
    ]
    cursor = db.events.aggregate(pipeline_top)
    top_domain_doc = await cursor.to_list(length=1)
    
    top_domain = top_domain_doc[0]["_id"] if len(top_domain_doc)>0 else "N/A"
    
    data = {
        "abiertos": abiertos,
        "criticos": criticos,
        "honeypots_hoy": honeypots_hoy,
        "mayor_riesgo_id": top_risk_id,
        "top_dominio_malicioso": top_domain
    }
    
    return success_response(data)
