import os
import json
import uuid
import asyncio
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter
from fastapi.responses import JSONResponse
import anthropic
from shared.logger import get_logger
from shared.mongo_client import MongoClient
from shared.redis_bus import RedisBus
from api.utils import success_response, error_response

router = APIRouter(prefix="/ai", tags=["ai"])
logger = get_logger("api.ai")
mongo_client = MongoClient()
redis_bus = RedisBus()

@router.get("/memos")
async def list_memos(limit: int = 20, offset: int = 0):
    col = mongo_client.db.ai_memos
    total = await col.count_documents({})
    
    cursor = col.find({}).sort("created_at", -1).skip(offset).limit(limit)
    memos = []
    async for doc in cursor:
        doc.pop("_id", None)
        memos.append(doc)
        
    return success_response(memos, total)

async def _correr_analisis_claude(incident_id: str, memo_id: str):
    try:
        incidente = await mongo_client.db.incidents.find_one({"id": incident_id})
        if not incidente: return
        
        host = incidente.get("host_afectado", "")
        desc = incidente.get("descripcion", "")
        tecnica = incidente.get("mitre_technique", "")
        sev = incidente.get("severidad", "BAJA")
        
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            # Fallback simulado si no config
            result = f"Análisis Automatizado simulado: El host {host} reporta {tecnica} ({sev}).\n\nRecomendaciones:\n1. Aislar host\n2. Rotar credenciales."
        else:
            client = anthropic.AsyncAnthropic(api_key=api_key)
            prompt = f"Incidente:\nHost: {host}\nDesc: {desc}\nSeveridad: {sev}\nMITRE: {tecnica}\nGenera un resumen analítico accionable para SoC"
            
            resp = await client.messages.create(
                model="claude-4.6-opus",
                max_tokens=500,
                temperature=0.2,
                system="Eres un experto analista SOC Nivel 3.",
                messages=[{"role": "user", "content": prompt}]
            )
            result = resp.content[0].text if resp.content else "Nada"

        memo = {
            "id": memo_id,
            "incident_id": incident_id,
            "contenido": result,
            "generado_por": "Claude 4.6 Opus",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        await mongo_client.db.ai_memos.insert_one(memo)
        
        # Publicar notificación por canal de WebSockets
        try:
            r = redis_bus.client
            if r:
                await r.publish("channel:ai_updates", json.dumps(memo))
        except Exception:
            pass
            
    except Exception as e:
        logger.error(f"Análisis IA abortado para {incident_id}: {e}")

@router.post("/analyze/{incident_id}")
async def analyze_incident(incident_id: str):
    # Verifico que exista
    ext = await mongo_client.db.incidents.find_one({"id": incident_id})
    if not ext:
        return JSONResponse(status_code=404, content=error_response("Incidente no encontrado", "NOT_FOUND"))
        
    memo_id = f"MEMO-{uuid.uuid4().hex[:8]}"
    
    # Procesamiento Fire and Forget
    asyncio.create_task(_correr_analisis_claude(incident_id, memo_id))
    
    return success_response({"status": "processing", "memo_id": memo_id})

@router.post("/ceo-view")
async def generar_ceo_view():
    """Reporte Ejecutivo (Synchronous await)."""
    try:
        hoy = datetime.now(timezone.utc).replace(hour=0, minute=0, microsecond=0).isoformat()
        inc_count = await mongo_client.db.incidents.count_documents({"timestamp": {"$gte": hoy}})
        criticos = await mongo_client.db.incidents.count_documents({"severidad": {"$in": ["CRÍTICA", "CRITICA"]}})
        
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            return success_response({
                "titulo": "Estado de Ciberseguridad Diaria",
                "resumen": f"El SOC procesó tráfico general sin interrupciones. Se detectaron {inc_count} incidentes de seguridad, conteniendo {criticos} alertas críticas originadas por sensores internos.",
                "acciones": "Monitoreo continuo en nivel estable."
            })
            
        client = anthropic.AsyncAnthropic(api_key=api_key)
        prompt = f"Actualmente registramos {inc_count} incidentes hoy, incluyendo {criticos} nivel critico. Escribe un párrafo directivo de informe CEO de 3 frases informando la postura."
        
        resp = await client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=300,
            temperature=0.3,
            system="Eres un CISO informando de manera calmada pero firme al Board Administrativo sobre reportes diarios SIEM.",
            messages=[{"role": "user", "content": prompt}]
        )
        
        result = resp.content[0].text if resp.content else ""
        return success_response({
            "titulo": "Executive Cyber Posture",
            "resumen": result,
            "acciones": ""
        })
    except Exception as e:
        logger.error(f"CEO View Crash: {e}")
        return JSONResponse(status_code=500, content=error_response("Falla en Generación IA", "AI_FAIL"))