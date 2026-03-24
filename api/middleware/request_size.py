"""
Límite de tamaño de petición por cabecera Content-Length (PROMPTS_V6 S02).
"""

from __future__ import annotations

import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

MAX_REQUEST_SIZE = 1 * 1024 * 1024


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Rechaza cuerpos mayores a MAX_REQUEST_SIZE si Content-Length lo declara."""

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        raw = request.headers.get("content-length")
        if raw is not None and str(raw).strip() != "":
            try:
                n = int(str(raw).strip())
            except ValueError:
                rid = str(uuid.uuid4())[:8]
                r = Response(
                    content='{"error": "Content-Length inválido"}',
                    status_code=400,
                    media_type="application/json",
                )
                r.headers["X-Request-ID"] = rid
                return r
            if n > MAX_REQUEST_SIZE:
                rid = str(uuid.uuid4())[:8]
                r = Response(
                    content='{"error": "Request demasiado grande"}',
                    status_code=413,
                    media_type="application/json",
                )
                r.headers["X-Request-ID"] = rid
                return r
        return await call_next(request)
