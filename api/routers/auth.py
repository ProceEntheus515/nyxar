"""Login JWT y emisión de API keys (S01)."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status

from api.auth.audit import log_security_event
from api.auth.core import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    create_access_token,
    dummy_password_hash,
    generate_api_key,
    mongo_user_to_model,
    verify_password,
)
from api.auth.deps import get_db, require_admin
from api.auth.models import CreateApiKeyBody, LoginRequest, User
from api.auth.roles import ROLE_HIERARCHY
from api.middleware.rate_limit import limiter

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login")
@limiter.limit("5/minute", override_defaults=False)
async def login(credentials: LoginRequest, request: Request, db=Depends(get_db)) -> dict:
    user = await db.users.find_one({"username": credentials.username.strip()})
    stored_hash = (
        user.get("password_hash", dummy_password_hash())
        if user
        else dummy_password_hash()
    )
    password_valid = verify_password(credentials.password, stored_hash)

    if not user or not password_valid or not user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas",
        )

    await log_security_event(db, "login_success", user["username"], request)

    await db.users.update_one(
        {"_id": user["_id"]},
        {"$set": {"last_login": datetime.now(timezone.utc)}},
    )

    u = mongo_user_to_model(user)
    token = create_access_token(u)
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "role": user["role"],
    }


@router.post("/api-keys")
@limiter.limit("10/hour", override_defaults=False)
async def create_api_key(
    body: CreateApiKeyBody,
    request: Request,
    db=Depends(get_db),
    current_user: User = Depends(require_admin),
) -> dict:
    if ROLE_HIERARCHY.get(body.role, 0) > ROLE_HIERARCHY.get(current_user.role, 0):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No podés crear una API key con rol superior al tuyo",
        )

    key_plain, key_hash = generate_api_key()
    prefix = key_plain[:10] + "..."

    await db.api_keys.insert_one(
        {
            "name": body.name.strip(),
            "key_hash": key_hash,
            "role": body.role,
            "user_id": current_user.id,
            "created_at": datetime.now(timezone.utc),
            "last_used": None,
            "is_active": True,
            "key_prefix": prefix,
        }
    )

    await log_security_event(
        db,
        "api_key_created",
        current_user.username,
        request,
        extra={"key_name": body.name, "role": body.role},
    )

    return {
        "key": key_plain,
        "prefix": prefix,
        "warning": "Esta key no puede recuperarse. Guardala ahora.",
    }
