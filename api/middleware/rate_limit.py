"""
Rate limiting distribuido (S10) vía slowapi + Redis.
"""

from __future__ import annotations

import os

from slowapi import Limiter
from slowapi.util import get_remote_address

# Redis compartido: varias réplicas de la API comparten contadores.
# Sin REDIS_URL se usa memoria (tests / arranque mínimo).
_storage_uri = (os.getenv("REDIS_URL") or "").strip() or "memory://"

limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=_storage_uri,
    default_limits=["200/minute"],
    headers_enabled=True,
    in_memory_fallback_enabled=True,
)

# Referencia de límites por ruta (los valores efectivos están en los decoradores).
ENDPOINT_LIMITS = {
    "POST /api/v1/auth/login": "5/minute",
    "POST /api/v1/auth/api-keys": "10/hour",
    "POST /api/v1/ai/ceo-view": "10/hour",
    "POST /api/v1/ai/analyze": "20/hour",
    "POST /api/v1/hunting/hypotheses": "30/hour",
    "POST /api/v1/simulator/scenario": "20/hour",
    "GET /api/v1/events": "300/minute",
    "GET /api/v1/identity": "60/minute",
}
