"""
Audit log de seguridad del propio NYXAR (S13): append-only, sin secretos.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Optional, TYPE_CHECKING

from fastapi import Request

from shared.logger import get_logger

if TYPE_CHECKING:
    from shared.redis_bus import RedisBus

logger = get_logger("api.auth.audit")

SECURITY_AUDIT_COLLECTION = "security_audit_log"

# Eventos que disparan notificación inmediata al dashboard (PubSub).
CRITICAL_EVENTS_ALERT = frozenset(
    {
        "login_failure_repeated",
        "permission_denied_repeated",
        "prompt_injection_detected",
    }
)

_SENSITIVE_EXTRA_KEYS = frozenset(
    {
        "password",
        "token",
        "access_token",
        "refresh_token",
        "secret",
        "authorization",
        "api_key",
        "key",
        "password_hash",
    }
)


def _get_severity(event_type: str) -> str:
    critical = {"prompt_injection_detected", "login_failure_repeated"}
    high = {"permission_denied_repeated", "api_key_revoked"}
    medium = {
        "login_failure",
        "permission_denied",
        "rate_limit_exceeded",
    }
    if event_type in critical:
        return "critical"
    if event_type in high:
        return "high"
    if event_type in medium:
        return "medium"
    return "info"


def _sanitize_extra(extra: Optional[dict[str, Any]]) -> dict[str, Any]:
    if not extra:
        return {}
    out: dict[str, Any] = {}
    for k, v in extra.items():
        lk = str(k).lower()
        if lk in _SENSITIVE_EXTRA_KEYS or any(s in lk for s in ("password", "token", "secret")):
            continue
        if isinstance(v, dict):
            out[k] = _sanitize_extra(v)
        else:
            out[k] = v
    return out


def _client_host(request: Optional[Request]) -> Optional[str]:
    if request is None or request.client is None:
        return None
    return request.client.host


def _redis_key_actor(actor: str) -> str:
    """Evita caracteres que rompan la clave Redis o permitan colisiones raras."""
    s = (actor or "unknown").strip()[:200]
    return re.sub(r"[^a-zA-Z0-9_.@-]", "_", s) or "unknown"


async def log_security_event(
    event_type: str,
    actor: str,
    *,
    request: Optional[Request] = None,
    extra: Optional[dict[str, Any]] = None,
    db: Any = None,
    redis_bus: Optional["RedisBus"] = None,
) -> None:
    """
    Inserta en security_audit_log (inmutable vía diseño: sin rutas de update/delete en API).
    No guardar passwords ni tokens en extra.
    """
    now = datetime.now(timezone.utc)
    entry: dict[str, Any] = {
        "timestamp": now,
        "event_type": event_type,
        "actor": (actor or "unknown")[:512],
        "ip_address": _client_host(request),
        "user_agent": (
            (request.headers.get("user-agent") or "")[:2000] if request else ""
        ),
        "endpoint": (request.url.path[:2000] if request else None),
        "method": (request.method if request else None),
        "extra": _sanitize_extra(extra),
        "severity": _get_severity(event_type),
    }

    if db is not None:
        try:
            await db[SECURITY_AUDIT_COLLECTION].insert_one(entry)
        except Exception as e:
            logger.warning("security_audit_log insert failed: %s", e)

    logger.info(
        "SECURITY_EVENT %s actor=%s ip=%s",
        event_type,
        entry["actor"],
        entry.get("ip_address"),
    )

    if event_type in CRITICAL_EVENTS_ALERT and redis_bus is not None:
        client = getattr(redis_bus, "client", None)
        if client is not None:
            try:
                await redis_bus.publish_alert(
                    "dashboard:alerts",
                    {
                        "tipo": "security_event",
                        "event_type": event_type,
                        "actor": entry["actor"],
                        "timestamp": now.isoformat(),
                    },
                )
            except Exception as e:
                logger.warning("audit publish_alert failed: %s", e)


async def check_brute_force(
    actor: str,
    event_type: str,
    redis_client: Any,
    *,
    db: Any = None,
    request: Optional[Request] = None,
    redis_bus: Optional["RedisBus"] = None,
    threshold: int = 5,
    window_seconds: int = 300,
) -> bool:
    """
    Cuenta fallos por actor+tipo en ventana fija. Si supera threshold,
    registra {event_type}_repeated y devuelve True (p. ej. bloquear login).
    """
    if redis_client is None:
        return False
    key = f"security:brute_force:{event_type}:{_redis_key_actor(actor)}"
    try:
        count = await redis_client.incr(key)
        if count == 1:
            await redis_client.expire(key, window_seconds)
        if count >= threshold:
            await log_security_event(
                f"{event_type}_repeated",
                actor or "unknown",
                request=request,
                extra={"count": count, "window_seconds": window_seconds},
                db=db,
                redis_bus=redis_bus,
            )
            return True
    except Exception as e:
        logger.warning("check_brute_force redis error: %s", e)
    return False


async def clear_brute_force_counter(
    actor: str,
    event_type: str,
    redis_client: Any,
) -> None:
    if redis_client is None:
        return
    key = f"security:brute_force:{event_type}:{_redis_key_actor(actor)}"
    try:
        await redis_client.delete(key)
    except Exception as e:
        logger.warning("clear_brute_force_counter: %s", e)
