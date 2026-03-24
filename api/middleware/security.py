"""
Cabeceras de seguridad, request ID, métodos bloqueados y validación ligera de Content-Type.
No registrar el body: puede contener credenciales (PROMPTS_V6 S02).
"""

from __future__ import annotations

import time
import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from shared.logger import get_logger

logger = get_logger("api.middleware.security")


def _apply_response_security_headers(response: Response, request_id: str) -> None:
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"
    if "server" in response.headers:
        del response.headers["server"]
    if "x-powered-by" in response.headers:
        del response.headers["x-powered-by"]


def _path_exempt_from_json_only(path: str) -> bool:
    """Rutas donde Engine.IO / Socket.IO o descargas no usan application/json."""
    p = path or ""
    if "/download" in p:
        return True
    if "socket.io" in p:
        return True
    return False


def _has_message_body(request: Request) -> bool:
    """True si el cliente declara cuerpo con tamaño > 0."""
    raw = request.headers.get("content-length")
    if raw is None or str(raw).strip() == "":
        return False
    try:
        return int(str(raw).strip()) > 0
    except ValueError:
        return True


class SecurityMiddleware(BaseHTTPMiddleware):
    """Request ID, bloqueo TRACE/CONNECT, JSON-only con body, security headers en respuesta."""

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = str(uuid.uuid4())[:8]
        request.state.request_id = request_id

        start_time = time.perf_counter()

        if request.method in ("TRACE", "CONNECT"):
            r = Response(status_code=405)
            _apply_response_security_headers(r, request_id)
            return r

        if request.method in ("POST", "PUT", "PATCH") and not _path_exempt_from_json_only(
            request.url.path
        ):
            if _has_message_body(request):
                content_type = request.headers.get("content-type", "")
                if "application/json" not in content_type:
                    r = Response(
                        content='{"error": "Content-Type debe ser application/json"}',
                        status_code=415,
                        media_type="application/json",
                    )
                    _apply_response_security_headers(r, request_id)
                    return r

        response = await call_next(request)

        _apply_response_security_headers(response, request_id)

        duration_ms = (time.perf_counter() - start_time) * 1000
        logger.info(
            "[%s] %s %s -> %s (%.0fms)",
            request_id,
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )

        return response
