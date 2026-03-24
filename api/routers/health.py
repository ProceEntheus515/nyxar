"""
Health ligero (/health) y detallado (/health/detail) con clave de cabecera.
"""

from __future__ import annotations

import os

from fastapi import APIRouter, Depends, Header, HTTPException, Request

from observability.health import HealthChecker, quick_health
from api.middleware.rate_limit import limiter

router = APIRouter(tags=["health"])


async def require_health_detail_key(
    x_nyxar_health_key: str | None = Header(None, alias="X-Nyxar-Health-Key"),
) -> None:
    expected = (os.getenv("HEALTH_DETAIL_API_KEY") or "").strip()
    if not expected:
        raise HTTPException(
            status_code=503,
            detail="HEALTH_DETAIL_API_KEY no está configurada en el servidor",
        )
    if not x_nyxar_health_key or x_nyxar_health_key.strip() != expected:
        raise HTTPException(status_code=401, detail="Clave de detalle de salud inválida")


@router.get("/health")
@limiter.exempt
async def health_live(request: Request) -> dict:
    redis_bus = getattr(request.app.state, "redis_bus", None)
    mongo = getattr(request.app.state, "mongo_client", None)
    if redis_bus is None or mongo is None:
        raise HTTPException(status_code=503, detail="Servicio iniciando")
    return await quick_health(redis_bus, mongo)


@router.get("/health/detail", dependencies=[Depends(require_health_detail_key)])
@limiter.exempt
async def health_detail(request: Request) -> dict:
    redis_bus = getattr(request.app.state, "redis_bus", None)
    mongo = getattr(request.app.state, "mongo_client", None)
    if redis_bus is None or mongo is None:
        raise HTTPException(status_code=503, detail="Servicio iniciando")
    checker = HealthChecker(redis_bus, mongo)
    report = await checker.full_check()
    return report.model_dump(mode="json")
