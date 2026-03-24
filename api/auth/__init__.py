"""Autenticación NYXAR (JWT + API keys, S01)."""

from api.auth.bootstrap import ensure_auth_startup
from api.auth.core import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    create_access_token,
    generate_api_key,
    verify_api_key,
    verify_password,
)
from api.auth.deps import (
    get_current_user,
    get_db,
    require_admin,
    require_analyst,
    require_operator,
    require_role,
    require_viewer,
)
from api.auth.models import User

__all__ = [
    "ACCESS_TOKEN_EXPIRE_MINUTES",
    "User",
    "create_access_token",
    "ensure_auth_startup",
    "generate_api_key",
    "get_current_user",
    "get_db",
    "require_admin",
    "require_analyst",
    "require_operator",
    "require_role",
    "require_viewer",
    "verify_api_key",
    "verify_password",
]
