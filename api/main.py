import asyncio
import os
from contextlib import asynccontextmanager
from typing import Dict, Any
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timezone

from shared.logger import get_logger
from shared.mongo_client import MongoClient
from shared.redis_bus import RedisBus
from shared.heartbeat import heartbeat_loop

# Routers
from api.routers import events, identities, incidents, alerts, simulator, ai, response, response_proposals, hunting, notifications
from api.routers.health import router as health_router
from api.routers.identity import router as identity_router, ensure_nyxar_start_time
from api.routers.response import ensure_response_audit_indexes
from api.routers.hunting import ensure_hunting_indexes
from auto_response.approval import ApprovalManager
from auto_response.audit import AuditLogger

logger = get_logger("api.main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_nyxar_start_time()
    # Inicializar conexiones
    redis_bus = RedisBus()
    mongo_client = MongoClient()
    
    await redis_bus.connect()
    await mongo_client.connect()
    app.state.redis_bus = redis_bus
    app.state.mongo_client = mongo_client
    await ensure_response_audit_indexes()
    await ensure_hunting_indexes()
    logger.info("Conexiones de API a Redis y MongoDB establecidas.")

    async def approval_expire_poll() -> None:
        await asyncio.sleep(60)
        try:
            poll_s = max(60, int(os.getenv("APPROVAL_EXPIRE_POLL_S", "900") or "900"))
        except ValueError:
            poll_s = 900
        while True:
            try:
                am = ApprovalManager(mongo_client, None, AuditLogger(mongo_client))
                n = await am.auto_expire()
                if n:
                    logger.info("APPROVAL expire (API): %s propuestas", n)
            except Exception as e:
                logger.warning("APPROVAL expire poll: %s", e)
            await asyncio.sleep(poll_s)

    hb_task = asyncio.create_task(heartbeat_loop(redis_bus, "api"), name="api-hb")
    expire_task = asyncio.create_task(approval_expire_poll())

    yield

    for t in (hb_task, expire_task):
        t.cancel()
        try:
            await t
        except asyncio.CancelledError:
            pass
    await redis_bus.disconnect()
    await mongo_client.disconnect()
    logger.info("API apagada.")

app = FastAPI(
    title="NYXAR API",
    version="1.0.0",
    lifespan=lifespan
)

# CORS Middleware
origins = [
    "http://localhost:3000",
    "http://localhost:5173"
]
prod_cors = os.getenv("FRONTEND_CORS_URL")
if prod_cors:
    origins.append(prod_cors)
    
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception Handler custom de fallback estandarizado
@app.exception_handler(Exception)
async def custom_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global API Error: {exc} | Path: {request.url.path}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Error interno en el servidor",
            "code": "INTERNAL_ERROR",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )

# Routers inclusions
from api.websocket import socket_app

app.include_router(events.router, prefix="/api/v1")
app.include_router(identity_router, prefix="/api/v1")
app.include_router(identities.router, prefix="/api/v1")
app.include_router(incidents.router, prefix="/api/v1")
app.include_router(alerts.router, prefix="/api/v1")
app.include_router(ai.router, prefix="/api/v1")
app.include_router(response.router, prefix="/api/v1")
app.include_router(response_proposals.router, prefix="/api/v1")
app.include_router(hunting.router, prefix="/api/v1")
app.include_router(notifications.router, prefix="/api/v1")
app.include_router(health_router)

if os.getenv("LAB_MODE", "false").lower() == "true":
    app.include_router(simulator.router, prefix="/api/v1")

# Standard Wrapper Function para retornar {"data": ..., "total": N, "timestamp": "..."}
def success_response(data: Any, total: int = None) -> Dict[str, Any]:
    res = {
        "data": data,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    if total is not None:
        res["total"] = total
    return res

@app.get("/")
async def root():
    return RedirectResponse(url="/api/v1/identity", status_code=302)


# Mount final del ASGI de SocketIO envolviendo si es necesario o en ruta
app.mount("/", socket_app)
