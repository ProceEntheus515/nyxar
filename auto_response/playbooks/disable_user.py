"""
Deshabilitar usuario en AD: requiere AD_WRITE_ENABLED.
v1: stub que solo audita la intención (LDAP write no implementado aquí).
"""

from __future__ import annotations

import os
from typing import Any, Dict

from shared.logger import get_logger

from auto_response.models import AccionPropuesta
from auto_response.playbooks.base import PlaybookBase

logger = get_logger("auto_response.playbooks.disable_user")


class DisableUserPlaybook(PlaybookBase):
    nombre = "disable_user"

    async def execute(
        self,
        accion: AccionPropuesta,
        contexto: Dict[str, Any],
    ) -> Dict[str, Any]:
        enabled = os.getenv("AD_WRITE_ENABLED", "").strip().lower() in (
            "1",
            "true",
            "yes",
        )
        if not enabled:
            logger.warning(
                "DisableUserPlaybook: AD_WRITE_ENABLED=false; stub para usuario=%s",
                accion.objetivo,
            )
            return {
                "exito": True,
                "detalle": "skipped: AD_WRITE_ENABLED=false (stub v1)",
                "payload_redactado": {"usuario": accion.objetivo},
            }
        logger.error(
            "DisableUserPlaybook: AD_WRITE_ENABLED true pero LDAP write no implementado en v1: %s",
            accion.objetivo,
        )
        return {
            "exito": False,
            "detalle": "LDAP disable_user no implementado; desactivar AD_WRITE_ENABLED o ampliar modulo",
            "payload_redactado": {"usuario": accion.objetivo},
        }
