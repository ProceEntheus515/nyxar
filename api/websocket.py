import os
import json
import asyncio
from typing import Dict, List
import socketio
from datetime import datetime, timezone

from shared.logger import get_logger
from shared.redis_bus import RedisBus
from shared.mongo_client import MongoClient

logger = get_logger("api.websocket")

# Socket.IO ASGI Server (Permite CORS, maneja Heartbeats pings de 25s automáticamente)
sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins="*")

# State management
mongo_client = MongoClient()
redis_bus = RedisBus()
active_tasks = []

# Queues / Buffers para Rate Limiting
event_queue = asyncio.Queue()
identity_updates: Dict[str, dict] = {} # buffer de identity risk deltas

@sio.event
async def connect(sid, environ):
    logger.info(f"[WS] Cliente conectado: {sid}")
    db = mongo_client.db
    
    try:
        # 1. Traer Últimos 10 eventos
        cursor_ev = db.events.find().sort("timestamp", -1).limit(10)
        evs = [doc async for doc in cursor_ev]
        for e in evs: e.pop("_id", None)
            
        # 2. Identidades con risk_score > 40
        cursor_id = db.identities.find({"risk_score": {"$gt": 40}}).sort("risk_score", -1)
        idents = [doc async for doc in cursor_id]
        for i in idents: i.pop("_id", None)
            
        # 3. Últimos 5 memos de IA
        cursor_ai = db.ai_memos.find().sort("created_at", -1).limit(5)
        memos = [doc async for doc in cursor_ai]
        for m in memos: m.pop("_id", None)
            
        await sio.emit("initial_state", {
            "last_events": evs,
            "risk_identities": idents,
            "ai_memos": memos
        }, room=sid)
        
    except Exception as e:
        logger.error(f"[WS] Fallo enviando payload inicial a {sid}: {e}")

@sio.event
async def disconnect(sid):
    logger.info(f"[WS] Cliente desconectado: {sid}")
    # Socket.IO limpia las rooms automáticamente al desconectar

@sio.event
async def subscribe_identity(sid, data):
    # Cliente pide monitorear una identidad especifica
    iden_id = data.get("identidad_id")
    if iden_id:
        room_name = f"identity:{iden_id}"
        await sio.enter_room(sid, room_name)
        logger.debug(f"[WS] Cliente {sid} suscrito a {room_name}")

@sio.event
async def request_ceo_view(sid, data):
    from api.routers.ai import generar_ceo_view
    # Genera el CEO view asincronamente
    try:
        res = await generar_ceo_view()
        if hasattr(res, 'body'):
             dict_res = json.loads(res.body.decode())
        else:
             dict_res = res
             
        memo_fake = {
            "id": f"MEMO-CEO-{uuid.uuid4().hex[:6]}",
            "incident_id": "GLOBAL",
            "contenido": dict_res.get("data", {}).get("resumen", "No generado"),
            "generado_por": "Claude 3.5 Sonnet (CEO Report)",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await sio.emit("ai_memo", memo_fake, room=sid)
    except Exception as e:
        logger.error(f"[WS] Fallo generando ceo view manual: {e}")

async def event_dispatcher_loop():
    """Consume eventos de la cola en memoria con rate limit estricto (Max 50/s) agrupando en batches."""
    batch = []
    
    while True:
        try:
            # Acumulamos de la cola todos los posibles durante 1 segundo
            while not event_queue.empty() and len(batch) < 50:
                evento = event_queue.get_nowait()
                batch.append(evento)
                
            if batch:
                if len(batch) > 1:
                    # Dividimos en chunks si excede 20 para agrupar 
                    chunks = [batch[i:i+20] for i in range(0, len(batch), 20)]
                    for chunk in chunks:
                        await sio.emit("new_event_batch", {"events": chunk})
                else:
                    evento = batch[0]
                    await sio.emit("new_event", evento)
                    # Si toca room especifico
                    ip = evento["interno"].get("ip") if "interno" in evento else None
                    if ip:
                        await sio.emit("new_event", evento, room=f"identity:{ip}")
                        
                batch.clear()
                
            await asyncio.sleep(1.0) # Rate limit real 1 iteración/segundo emitiendo max 50 evts
        except Exception as e:
            logger.error(f"[WS] Falla en dispatcher de eventos: {e}")
            await asyncio.sleep(1.0)

async def identity_updater_loop():
    """Despacha risk updates retenidos (Max 1 update x ident / segundo)"""
    while True:
        try:
            if identity_updates:
                updates = list(identity_updates.values())
                identity_updates.clear()
                for upd in updates:
                    await sio.emit("identity_update", upd)
            await asyncio.sleep(1.0)
        except Exception as e:
            pass

async def stats_loop():
    while True:
        try:
            db = mongo_client.db
            eventos_min = await db.events.count_documents({"timestamp": {"$gte": (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()}})
            activas = await db.identities.count_documents({"last_seen": {"$gte": (datetime.now(timezone.utc) - timedelta(hours=24))}})
            abiertas = await db.incidents.count_documents({"estado": {"$nin": ["cerrado", "falso_positivo"]}})
            
            await sio.emit("stats_update", {
                "eventos_por_min": eventos_min,
                "identidades_activas": activas,
                "alertas_abiertas": abiertas
            })
        except Exception:
            pass
        await asyncio.sleep(30.0)

async def redis_listener():
    """Puente unificado. Escucha pub/sub crudo de alert/ai, 
    y para eventos el canal dashboard:events (como requiere la arquitectura)."""
    r = redis_bus.client
    if not r: return
    
    pubsub = r.pubsub()
    channels = [
        "dashboard:events",
        "channel:ai_updates",
        "alerts",
        "notifications:urgent",
    ]
    await pubsub.subscribe(*channels)
    
    logger.info(f"[WS] Escuchando canales Redis: {channels}")
    
    async for msg in pubsub.listen():
        if msg['type'] == 'message':
            try:
                raw = msg["data"]
                data = json.loads(raw.decode() if isinstance(raw, bytes) else raw)
                ch = msg["channel"]
                chan = ch.decode() if isinstance(ch, bytes) else ch
                
                if chan == "dashboard:events":
                    evt_type = data.get("type")
                    payload = data.get("payload")
                    
                    if evt_type == "new_event":
                        await event_queue.put(payload)
                    elif evt_type == "new_alert":
                         # Prioridad: va directo
                         await sio.emit("new_alert", payload)
                    elif evt_type == "honeypot_hit":
                         await sio.emit("honeypot_hit", payload)
                    elif evt_type == "identity_update":
                         identity_updates[payload["identidad_id"]] = payload
                         
                elif chan == "channel:ai_updates":
                    await sio.emit("ai_memo", data)
                    
                elif chan in ("alerts", "notifications:urgent"):
                    # Mappeo legado de RedisBus publish_alert + canal urgente SOAR
                    if "honeypot_name" in data or data.get("patron") == "TRAMPILLA_HONEYPOT":
                        await sio.emit("honeypot_hit", data)
                    else:
                        await sio.emit("new_alert", data)
                        
            except Exception as e:
                 logger.error(f"[WS] Error parseando Redis PubSub: {e} | {msg['data']}")

def start_background_tasks():
    global active_tasks
    if not active_tasks:
        active_tasks.append(asyncio.create_task(event_dispatcher_loop()))
        active_tasks.append(asyncio.create_task(identity_updater_loop()))
        active_tasks.append(asyncio.create_task(stats_loop()))
        active_tasks.append(asyncio.create_task(redis_listener()))
        logger.info("[WS] Tareas en background iniciadas.")

# Wrapper para correr al iniciar FastAPI
socket_app = socketio.ASGIApp(sio, on_startup=start_background_tasks)
