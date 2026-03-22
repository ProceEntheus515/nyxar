"""
API de preferencias de notificación, historial (notifications_log), estadísticas y prueba de canales.
Si NOTIFY_API_KEY está definida, las mutaciones exigen header X-Notify-Api-Key.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any, Literal, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from api.utils import error_response, success_response
from notifier.channels.email import EmailChannel
from notifier.channels.whatsapp import WhatsAppChannel
from notifier.models import NotifMessage, Recipient
from notifier.preferences_manager import (
    DEFAULT_POLICY,
    PreferencesManager,
    get_all_admins_from_env,
    get_area_responsible_from_env,
    _parse_channels_enabled,
)
from shared.logger import get_logger
from shared.mongo_client import MongoClient
from shared.redis_bus import RedisBus

logger = get_logger("api.notifications")

router = APIRouter(prefix="/notifications", tags=["notifications"])

mongo_client = MongoClient()
redis_bus = RedisBus()

LOG_COLLECTION = "notifications_log"
_pref_manager: PreferencesManager | None = None
_log_indexes_ensured = False


async def _ensure_redis() -> None:
    if not redis_bus.client:
        try:
            await redis_bus.connect()
        except Exception as e:
            logger.warning("Redis notificaciones: %s", e)


async def get_preferences_manager() -> PreferencesManager:
    global _pref_manager
    await mongo_client.connect()
    await _ensure_redis()
    if _pref_manager is None:
        _pref_manager = PreferencesManager(mongo_client.db, lambda: redis_bus.client)
        await _pref_manager.ensure_indexes()
    return _pref_manager


async def ensure_notifications_log_indexes() -> None:
    global _log_indexes_ensured
    if _log_indexes_ensured:
        return
    try:
        await mongo_client.db[LOG_COLLECTION].create_index([("ts", -1)])
        await mongo_client.db[LOG_COLLECTION].create_index([("evento_tipo", 1)])
    except Exception as e:
        logger.warning("notifications_log indexes: %s", e)
    _log_indexes_ensured = True


def _require_write_api_key(x_notify_api_key: Optional[str] = Header(None, alias="X-Notify-Api-Key")) -> None:
    expected = (os.getenv("NOTIFY_API_KEY") or "").strip()
    if not expected:
        return
    got = (x_notify_api_key or "").strip()
    if got != expected:
        raise HTTPException(
            status_code=403,
            detail=error_response("API key de notificaciones inválida o ausente", "NOTIFY_API_KEY"),
        )


class SeverityFlags(BaseModel):
    email_enabled: bool = True
    whatsapp_enabled: bool = True


class PrefsBody(BaseModel):
    """Preferencias por severidad: solo flags, sin emails ni teléfonos."""

    critica: Optional[SeverityFlags] = None
    alta: Optional[SeverityFlags] = None
    media: Optional[SeverityFlags] = None
    baja: Optional[SeverityFlags] = None
    info: Optional[SeverityFlags] = None

    def as_severities_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for name in ("critica", "alta", "media", "baja", "info"):
            v = getattr(self, name, None)
            if v is not None:
                out[name] = v.model_dump()
        return out


class TestChannelBody(BaseModel):
    canal: Literal["email", "whatsapp"]
    severidad: str = "alta"


@router.get("/preferences")
async def get_notification_preferences(pm: PreferencesManager = Depends(get_preferences_manager)):
    effective = await pm.get_global_prefs()
    gdoc = await pm.get_global_document()
    return success_response(
        {
            "default_policy": DEFAULT_POLICY,
            "channels_enabled": sorted(_parse_channels_enabled()),
            "effective_global_flags": effective,
            "stored_global_document": gdoc,
            "engine_note": "NotificationEngine consulta PreferencesManager (Mongo + Redis) por destinatario y severidad; si falla la inicialización, usa las preferencias del Recipient cargadas desde .env.",
        }
    )


@router.put("/preferences", dependencies=[Depends(_require_write_api_key)])
async def put_global_notification_preferences(
    body: PrefsBody,
    pm: PreferencesManager = Depends(get_preferences_manager),
):
    try:
        updated = await pm.set_global_preferences(body.as_severities_dict())
    except ValueError as e:
        return JSONResponse(status_code=400, content=error_response(str(e), "VALIDATION_ERROR"))
    return success_response({"updated": updated})


@router.put("/preferences/user/{user_id}", dependencies=[Depends(_require_write_api_key)])
async def put_user_notification_preferences(
    user_id: str,
    body: PrefsBody,
    pm: PreferencesManager = Depends(get_preferences_manager),
):
    try:
        updated = await pm.set_user_preferences(user_id, body.as_severities_dict())
    except ValueError as e:
        return JSONResponse(status_code=400, content=error_response(str(e), "VALIDATION_ERROR"))
    return success_response({"user_id": user_id, "updated": updated})


@router.put("/preferences/area/{area}", dependencies=[Depends(_require_write_api_key)])
async def put_area_notification_preferences(
    area: str,
    body: PrefsBody,
    pm: PreferencesManager = Depends(get_preferences_manager),
):
    try:
        updated = await pm.set_area_preferences(area, body.as_severities_dict())
    except ValueError as e:
        return JSONResponse(status_code=400, content=error_response(str(e), "VALIDATION_ERROR"))
    return success_response({"area": area, "updated": updated})


@router.get("/preferences/user/{user_id}")
async def get_user_prefs_snapshot(user_id: str, pm: PreferencesManager = Depends(get_preferences_manager)):
    doc = await pm.get_user_document(user_id)
    return success_response(doc)


@router.get("/preferences/effective/{user_id}")
async def get_effective_prefs_for_severity(
    user_id: str,
    severidad: str = Query("media"),
    area: Optional[str] = Query(None),
    pm: PreferencesManager = Depends(get_preferences_manager),
):
    prefs = await pm.get_for_recipient(user_id, severidad, area=area)
    return success_response(
        {
            "user_id": user_id,
            "severidad": severidad,
            "area": area,
            "email_enabled": prefs.email_enabled,
            "whatsapp_enabled": prefs.whatsapp_enabled,
        }
    )


@router.get("/log")
async def list_notifications_log(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    evento_tipo: Optional[str] = None,
    ok: Optional[bool] = None,
    canal: Optional[str] = Query(None, description="Filtra si este canal aparece en el array canales"),
):
    await mongo_client.connect()
    await ensure_notifications_log_indexes()
    q: dict[str, Any] = {}
    if evento_tipo:
        q["evento_tipo"] = evento_tipo
    if ok is not None:
        q["ok"] = ok
    if canal:
        q["canales"] = canal
    col = mongo_client.db[LOG_COLLECTION]
    total = await col.count_documents(q)
    cursor = col.find(q).sort("ts", -1).skip(offset).limit(limit)
    rows: list[dict[str, Any]] = []
    async for doc in cursor:
        doc.pop("_id", None)
        rows.append(doc)
    return success_response(rows, total=total)


@router.get("/stats")
async def notifications_stats():
    await mongo_client.connect()
    await ensure_notifications_log_indexes()
    now = datetime.now(timezone.utc)
    start = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    start_iso = start.isoformat()
    col = mongo_client.db[LOG_COLLECTION]
    match = {"ts": {"$gte": start_iso}}
    total_today = await col.count_documents(match)
    ok_true = await col.count_documents({**match, "ok": True})
    ok_false = await col.count_documents({**match, "ok": False})

    pipeline = [
        {"$match": {**match, "canales": {"$exists": True, "$ne": []}}},
        {"$unwind": "$canales"},
        {"$group": {"_id": "$canales", "count": {"$sum": 1}}},
    ]
    by_channel: list[dict[str, Any]] = []
    try:
        async for row in col.aggregate(pipeline):
            by_channel.append({"canal": row["_id"], "count": row["count"]})
    except Exception as e:
        logger.warning("notifications stats aggregate: %s", e)

    top_events = []
    try:
        pe = [
            {"$match": match},
            {"$group": {"_id": "$evento_tipo", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 10},
        ]
        async for row in col.aggregate(pe):
            top_events.append({"evento_tipo": row["_id"], "count": row["count"]})
    except Exception as e:
        logger.warning("notifications stats top events: %s", e)

    return success_response(
        {
            "since_utc": start_iso,
            "total": total_today,
            "ok_true": ok_true,
            "ok_false": ok_false,
            "by_channel": by_channel,
            "top_evento_tipo": top_events,
        }
    )


@router.post("/test", dependencies=[Depends(_require_write_api_key)])
async def test_notification_channel(body: TestChannelBody):
    test_email = (os.getenv("NOTIFY_TEST_EMAIL") or "").strip()
    test_wa = (os.getenv("NOTIFY_TEST_WHATSAPP") or "").strip()
    if body.canal == "email" and not test_email:
        return JSONResponse(
            status_code=400,
            content=error_response(
                "Definí NOTIFY_TEST_EMAIL en el entorno para pruebas de email", "MISSING_NOTIFY_TEST_EMAIL"
            ),
        )
    if body.canal == "whatsapp" and not test_wa:
        return JSONResponse(
            status_code=400,
            content=error_response(
                "Definí NOTIFY_TEST_WHATSAPP (E.164) para pruebas de WhatsApp",
                "MISSING_NOTIFY_TEST_WHATSAPP",
            ),
        )

    base_url = (os.getenv("NOTIFY_DASHBOARD_BASE_URL") or "").strip().rstrip("/")
    link = f"{base_url}/" if base_url else None
    msg = NotifMessage(
        tipo="alerta",
        severidad=body.severidad.upper(),
        titulo="Prueba de notificación NYXAR",
        cuerpo="Mensaje de prueba generado por POST /notifications/test.",
        cuerpo_corto="Prueba NYXAR. Revisar dashboard.",
        link=link,
    )

    await _ensure_redis()
    if body.canal == "email":
        r = Recipient(id="test", nombre="Test", email=test_email)
        ch = EmailChannel()
        ok = await ch.send(r, msg)
    else:
        r = Recipient(id="test", nombre="Test", whatsapp_number=test_wa)
        ch = WhatsAppChannel(redis_client_getter=lambda: redis_bus.client)
        ok = await ch.send(r, msg)

    return success_response({"sent": ok, "canal": body.canal})


@router.get("/admins")
async def list_notification_admins():
    return success_response([a.model_dump() for a in get_all_admins_from_env()])


@router.get("/area/{area}/responsible")
async def get_area_responsible(area: str):
    r = get_area_responsible_from_env(area)
    if not r:
        return JSONResponse(
            status_code=404,
            content=error_response("Sin responsable configurado para el área", "AREA_NOT_CONFIGURED"),
        )
    return success_response(r.model_dump())
