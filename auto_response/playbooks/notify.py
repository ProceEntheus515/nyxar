"""Notificación al operador (log + Redis alert)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from shared.logger import get_logger

from auto_response.models import AccionPropuesta
from auto_response.playbooks.base import PlaybookBase

logger = get_logger("auto_response.playbooks.notify")


class NotifyPlaybook(PlaybookBase):
    nombre = "notify"

    def __init__(self, redis_bus: Optional[Any] = None) -> None:
        self.redis_bus = redis_bus

    async def execute(
        self,
        accion: AccionPropuesta,
        contexto: Dict[str, Any],
    ) -> Dict[str, Any]:
        incident_id = contexto.get("incident_id", "")
        payload = {
            "tipo": "auto_response_proposal",
            "incident_id": incident_id,
            "accion": accion.tipo,
            "objetivo": accion.objetivo,
            "descripcion": accion.descripcion,
            "ts": datetime.now(timezone.utc).isoformat(),
        }
        logger.info(
            "NotifyPlaybook: %s",
            accion.descripcion,
            extra={"extra": payload},
        )
        if self.redis_bus and getattr(self.redis_bus, "client", None):
            try:
                # Mismo canal que escucha api/websocket (redis_listener).
                await self.redis_bus.publish_alert("alerts", payload)
            except Exception as e:
                logger.warning("Redis publish_alert fallo: %s", e)
                return {
                    "exito": True,
                    "detalle": f"Log OK; Redis fallo: {e}",
                    "payload_redactado": {"incident_id": incident_id},
                }
        return {
            "exito": True,
            "detalle": "Notificacion registrada",
            "payload_redactado": {"incident_id": incident_id},
        }
