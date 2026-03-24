"""Dependencias FastAPI: BD, usuario actual, roles."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import Depends, HTTPException, Request, Security, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer

from api.auth.audit import check_brute_force, log_security_event
from api.auth.core import mongo_user_to_model, verify_api_key, verify_token
from api.auth.models import User
from api.auth.roles import ROLE_HIERARCHY, Role

bearer_scheme = HTTPBearer(auto_error=False)
api_key_header = APIKeyHeader(name="X-NYXAR-Key", auto_error=False)


async def get_db(request: Request):
    mongo = request.app.state.mongo_client
    if mongo.db is None:
        await mongo.connect()
    return mongo.db


async def get_current_user(
    request: Request,
    bearer: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    api_key: Optional[str] = Security(api_key_header),
    db=Depends(get_db),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciales inválidas o ausentes",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if bearer and bearer.credentials:
        token_data = verify_token(bearer.credentials)
        if token_data:
            user = await db.users.find_one({"username": token_data.username})
            if user and user.get("is_active", True):
                return mongo_user_to_model(user)

    if api_key:
        cursor = db.api_keys.find({"is_active": True})
        stored_keys = await cursor.to_list(200)
        for stored_key in stored_keys:
            h = stored_key.get("key_hash") or ""
            if not h or not verify_api_key(api_key, h):
                continue
            await db.api_keys.update_one(
                {"_id": stored_key["_id"]},
                {"$set": {"last_used": datetime.now(timezone.utc)}},
            )
            uid = stored_key.get("user_id")
            user = None
            if uid:
                user = await db.users.find_one({"id": uid})
            if not user and uid:
                user = await db.users.find_one({"username": uid})
            if user and user.get("is_active", True):
                key_role = stored_key.get("role") or user.get("role")
                return mongo_user_to_model(user, role_override=key_role)

    raise credentials_exception


def require_role(minimum_role: str):
    async def role_checker(
        request: Request,
        user: User = Depends(get_current_user),
        db=Depends(get_db),
    ) -> User:
        if ROLE_HIERARCHY.get(user.role, 0) < ROLE_HIERARCHY.get(minimum_role, 0):
            redis_bus = getattr(request.app.state, "redis_bus", None)
            redis_client = getattr(redis_bus, "client", None) if redis_bus else None
            await log_security_event(
                "permission_denied",
                user.username,
                request=request,
                extra={"required_role": minimum_role, "actual_role": user.role},
                db=db,
                redis_bus=redis_bus,
            )
            await check_brute_force(
                user.username,
                "permission_denied",
                redis_client,
                db=db,
                request=request,
                redis_bus=redis_bus,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Se requiere rol '{minimum_role}' o superior",
            )
        return user

    return role_checker


require_viewer = require_role(Role.VIEWER)
require_analyst = require_role(Role.ANALYST)
require_operator = require_role(Role.OPERATOR)
require_admin = require_role(Role.ADMIN)
