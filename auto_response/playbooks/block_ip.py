"""Bloqueo de IP vía API de firewall (opcional)."""

from __future__ import annotations

import os
from typing import Any, Dict

import httpx

from shared.logger import get_logger

from auto_response.models import AccionPropuesta
from auto_response.playbooks.base import PlaybookBase

logger = get_logger("auto_response.playbooks.block_ip")


class BlockIPPlaybook(PlaybookBase):
    nombre = "block_ip"

    async def execute(
        self,
        accion: AccionPropuesta,
        contexto: Dict[str, Any],
    ) -> Dict[str, Any]:
        url = (os.getenv("FIREWALL_API_URL") or "").strip()
        if not url:
            logger.warning(
                "BlockIPPlaybook: FIREWALL_API_URL no definido; omitido para %s",
                accion.objetivo,
            )
            return {
                "exito": True,
                "detalle": "skipped: sin FIREWALL_API_URL",
                "payload_redactado": {"ip": accion.objetivo},
            }
        body = {
            "action": "block_ip",
            "ip": accion.objetivo,
            "source": "cyberpulse_auto_response",
        }
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                r = await client.post(url, json=body)
            ok = 200 <= r.status_code < 300
            return {
                "exito": ok,
                "detalle": f"HTTP {r.status_code}",
                "payload_redactado": {"ip": accion.objetivo, "status": r.status_code},
            }
        except Exception as e:
            logger.error("BlockIPPlaybook error: %s", e)
            return {
                "exito": False,
                "detalle": str(e),
                "payload_redactado": {"ip": accion.objetivo},
            }
