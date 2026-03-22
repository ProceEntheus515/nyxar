"""Aislamiento: mismo mecanismo que bloqueo de IP del host afectado (sin destruir datos)."""

from __future__ import annotations

from typing import Any, Dict

from shared.logger import get_logger

from auto_response.models import AccionPropuesta
from auto_response.playbooks.block_ip import BlockIPPlaybook
from auto_response.playbooks.base import PlaybookBase

logger = get_logger("auto_response.playbooks.quarantine")


class QuarantinePlaybook(PlaybookBase):
    nombre = "quarantine"

    def __init__(self) -> None:
        self._block = BlockIPPlaybook()

    async def execute(
        self,
        accion: AccionPropuesta,
        contexto: Dict[str, Any],
    ) -> Dict[str, Any]:
        logger.info(
            "QuarantinePlaybook: aislar host objetivo=%s",
            accion.objetivo,
        )
        return await self._block.execute(accion, contexto)
