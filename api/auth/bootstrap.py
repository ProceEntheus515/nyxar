"""Índices Mongo y usuario administrador inicial."""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone

from api.auth.core import hash_password, validate_jwt_config
from api.auth.roles import Role
from shared.logger import get_logger

logger = get_logger("api.auth.bootstrap")

USERS_COLLECTION = "users"
API_KEYS_COLLECTION = "api_keys"


async def ensure_auth_startup(mongo_client) -> None:
    validate_jwt_config()
    db = mongo_client.db
    if db is None:
        await mongo_client.connect()
        db = mongo_client.db

    try:
        await db[USERS_COLLECTION].create_index("username", unique=True)
    except Exception as e:
        logger.warning("users index username: %s", e)
    try:
        await db[API_KEYS_COLLECTION].create_index("key_hash", unique=True)
    except Exception as e:
        logger.warning("api_keys index key_hash: %s", e)

    admin_count = await db[USERS_COLLECTION].count_documents(
        {"role": Role.ADMIN, "is_active": True}
    )
    if admin_count > 0:
        return

    username = (os.environ.get("NYXAR_ADMIN_USER") or "").strip()
    password = os.environ.get("NYXAR_ADMIN_PASS")
    password = (password or "").strip() if password is not None else ""

    if not username or not password:
        raise RuntimeError(
            "No hay administradores en la base de datos. "
            "Definí NYXAR_ADMIN_USER y NYXAR_ADMIN_PASS para crear el primer administrador al arrancar."
        )

    now = datetime.now(timezone.utc)
    doc = {
        "id": str(uuid.uuid4()),
        "username": username,
        "password_hash": hash_password(password),
        "role": Role.ADMIN,
        "is_active": True,
        "created_at": now,
        "last_login": None,
    }
    await db[USERS_COLLECTION].insert_one(doc)
    logger.info("Usuario administrador inicial creado (username=%s)", username)
