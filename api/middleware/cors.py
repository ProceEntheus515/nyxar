"""
CORS estricto: orígenes explícitos vía NYXAR_ALLOWED_ORIGINS (PROMPTS_V6 S02).
Compatibilidad: si existe FRONTEND_CORS_URL y no está en la lista, se añade.
"""

from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


def _parse_origins(raw: str) -> list[str]:
    return [o.strip() for o in raw.split(",") if o.strip()]


def configure_cors(app: FastAPI) -> None:
    default_list = "http://localhost:3000,http://localhost:5173"
    raw = (os.environ.get("NYXAR_ALLOWED_ORIGINS") or default_list).strip()
    allowed_origins = _parse_origins(raw)

    extra = (os.environ.get("FRONTEND_CORS_URL") or "").strip()
    if extra and extra not in allowed_origins:
        allowed_origins.append(extra)

    if not allowed_origins:
        allowed_origins = _parse_origins(default_list)

    nyxar_env = (os.environ.get("NYXAR_ENV") or "development").strip().lower()
    if "*" in allowed_origins and nyxar_env == "production":
        raise ValueError(
            "CORS wildcard '*' no está permitido en producción. "
            "Configurar NYXAR_ALLOWED_ORIGINS con los orígenes exactos."
        )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=[
            "Authorization",
            "Content-Type",
            "X-NYXAR-Key",
            "X-Request-ID",
            "X-Nyxar-Health-Key",
            "X-Notify-Api-Key",
        ],
        expose_headers=["X-Request-ID"],
        max_age=3600,
    )
