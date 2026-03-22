"""Notificacion de incidente vía Redis (PROMPTS_V2)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from shared.logger import get_logger

from auto_response.models import AccionPropuesta, PlaybookResult
from auto_response.playbooks.base import BasePlaybook, playbook_result_to_audit_dict

logger = get_logger("auto_response.playbooks.notify")

CHANNEL_URGENT = "notifications:urgent"


class NotifyOnlyPlaybook(BasePlaybook):
    nombre = "Notificacion de incidente"
    descripcion = "Publica en Redis para el notifier; sin cambios en infraestructura."
    reversible = False

    def __init__(self, redis_bus: Optional[Any] = None) -> None:
        self.redis_bus = redis_bus

    async def check_preconditions(self, objetivo: str) -> tuple[bool, str]:
        return True, ""

    async def execute_core(
        self,
        objetivo: str,
        incident_id: str,
        ejecutado_by: str,
    ) -> PlaybookResult:
        now = datetime.now(timezone.utc)
        execution_id = str(uuid.uuid4())
        return PlaybookResult(
            execution_id=execution_id,
            playbook=self.nombre,
            objetivo=objetivo,
            exitoso=True,
            mensaje="Notificacion encolada en Redis (exito de envio lo gestiona el notifier).",
            detalles={"canal_urgente": CHANNEL_URGENT},
            ejecutado_at=now,
            puede_deshacer=False,
        )

    async def execute(
        self,
        accion: AccionPropuesta,
        contexto: Dict[str, Any],
    ) -> Dict[str, Any]:
        incident_id = str(contexto.get("incident_id") or "")
        ejecutado_by = str(contexto.get("ejecutado_by") or "auto")
        objetivo = (accion.objetivo or "").strip()

        pr = await self.execute_core(objetivo, incident_id, ejecutado_by)
        out = playbook_result_to_audit_dict(pr)

        payload = {
            "tipo": "playbook_notify_only",
            "incident_id": incident_id,
            "accion": accion.tipo,
            "objetivo": objetivo,
            "descripcion": accion.descripcion,
            "ejecutado_by": ejecutado_by,
            "execution_id": pr.execution_id,
            "ts": datetime.now(timezone.utc).isoformat(),
        }
        logger.info(
            "NotifyOnlyPlaybook: %s",
            accion.descripcion,
            extra={"extra": payload},
        )
        if self.redis_bus and getattr(self.redis_bus, "client", None):
            try:
                await self.redis_bus.publish_alert(CHANNEL_URGENT, payload)
                await self.redis_bus.publish_alert("alerts", payload)
            except Exception as e:
                logger.warning("NotifyOnlyPlaybook Redis publish: %s", e)
                pr = PlaybookResult(
                    execution_id=pr.execution_id,
                    playbook=self.nombre,
                    objetivo=objetivo,
                    exitoso=True,
                    mensaje=f"Log OK; Redis fallo: {e}",
                    detalles={"redis_error": str(e)},
                    ejecutado_at=datetime.now(timezone.utc),
                    puede_deshacer=False,
                )
                return playbook_result_to_audit_dict(pr)
        return out


# Compatibilidad con imports historicos
NotifyPlaybook = NotifyOnlyPlaybook
