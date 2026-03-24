"""Auditoría de seguridad sin datos sensibles (tokens/passwords)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import Request

from shared.logger import get_logger

logger = get_logger("api.auth.audit")

SECURITY_EVENTS_COLLECTION = "security_events"


def _client_host(request: Optional[Request]) -> Optional[str]:
    if request is None or request.client is None:
        return None
    return request.client.host


async def log_security_event(
    db,
    tipo: str,
    username: Optional[str],
    request: Optional[Request] = None,
    extra: Optional[dict[str, Any]] = None,
) -> None:
    """Inserta evento en Mongo; fallos silenciosos en log para no romper el flujo principal."""
    doc: dict[str, Any] = {
        "tipo": tipo,
        "username": username,
        "ts": datetime.now(timezone.utc).isoformat(),
        "ip": _client_host(request),
    }
    if extra:
        safe = {k: v for k, v in extra.items() if k not in ("password", "token", "access_token")}
        doc["extra"] = safe
    try:
        await db[SECURITY_EVENTS_COLLECTION].insert_one(doc)
    except Exception as e:
        logger.warning("security_events insert failed: %s", e)
