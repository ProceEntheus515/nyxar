"""JWT, API keys (SHA-256) y hashing de contraseñas."""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Optional, Tuple

from jose import JWTError, jwt
from passlib.context import CryptContext

from api.auth.models import TokenData, User
from api.auth.roles import Role

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 480

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

JWT_SECRET_MIN_LEN = 32

_dummy_bcrypt_hash = "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj4J/HS5OYou"


def validate_jwt_config() -> str:
    """Exige NYXAR_JWT_SECRET en entorno; sin valor por defecto (fail secure)."""
    raw = os.environ.get("NYXAR_JWT_SECRET")
    if not raw or not str(raw).strip():
        raise RuntimeError(
            "NYXAR_JWT_SECRET no está definida. Generá una clave segura (p. ej. openssl rand -hex 32)."
        )
    secret = str(raw).strip()
    if len(secret) < JWT_SECRET_MIN_LEN:
        raise RuntimeError(
            f"NYXAR_JWT_SECRET debe tener al menos {JWT_SECRET_MIN_LEN} caracteres."
        )
    return secret


def get_jwt_secret() -> str:
    return validate_jwt_config()


def create_access_token(user: User) -> str:
    secret = get_jwt_secret()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user.username,
        "role": user.role,
        "exp": now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        "iat": now,
        "jti": secrets.token_hex(16),
    }
    return jwt.encode(payload, secret, algorithm=ALGORITHM)


def verify_token(token: str) -> Optional[TokenData]:
    try:
        secret = get_jwt_secret()
        payload = jwt.decode(token, secret, algorithms=[ALGORITHM])
        return TokenData(
            username=str(payload["sub"]),
            role=str(payload.get("role", Role.VIEWER)),
            exp=payload.get("exp"),
        )
    except JWTError:
        return None


def generate_api_key() -> Tuple[str, str]:
    key = f"nyx_{secrets.token_urlsafe(32)}"
    key_hash = hashlib.sha256(key.encode("utf-8")).hexdigest()
    return key, key_hash


def verify_api_key(key: str, stored_hash: str) -> bool:
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
    try:
        return hmac.compare_digest(digest, stored_hash)
    except TypeError:
        return False


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def dummy_password_hash() -> str:
    return _dummy_bcrypt_hash


def mongo_user_to_model(doc: dict[str, Any], role_override: Optional[str] = None) -> User:
    """Construye User desde documento Mongo; nunca incluye password_hash."""
    d = {k: v for k, v in doc.items() if k not in ("_id", "password_hash")}
    if "id" not in d and doc.get("_id") is not None:
        d["id"] = str(doc["_id"])
    if role_override is not None:
        d["role"] = role_override
    if not d.get("created_at"):
        d["created_at"] = datetime.now(timezone.utc)
    return User.model_validate(d)
