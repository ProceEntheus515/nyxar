"""Contrato común de playbooks de ejecución (PROMPTS_V2)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict

from auto_response.models import AccionPropuesta, PlaybookResult


def playbook_result_to_audit_dict(pr: PlaybookResult) -> Dict[str, Any]:
    """Serializa PlaybookResult al dict que consume el motor y el audit."""
    det = pr.model_dump(mode="json")
    return {
        "exito": pr.exitoso,
        "detalle": pr.mensaje,
        "payload_redactado": {
            "objetivo": pr.objetivo,
            "execution_id": pr.execution_id,
            "puede_deshacer": pr.puede_deshacer,
            "detalles": pr.detalles,
        },
        "execution_id": pr.execution_id,
        "puede_deshacer": pr.puede_deshacer,
        "playbook_result": det,
    }


class BasePlaybook(ABC):
    nombre: str = ""
    descripcion: str = ""
    reversible: bool = False

    async def check_preconditions(self, objetivo: str) -> tuple[bool, str]:
        return True, ""

    @abstractmethod
    async def execute_core(
        self,
        objetivo: str,
        incident_id: str,
        ejecutado_by: str,
    ) -> PlaybookResult:
        """Logica principal; no debe lanzar (capturar errores y devolver PlaybookResult)."""
        raise NotImplementedError

    async def undo(self, execution_id: str) -> PlaybookResult:
        return PlaybookResult(
            execution_id=execution_id or "",
            playbook=self.nombre,
            objetivo="",
            exitoso=False,
            mensaje="Playbook no reversible o undo no implementado",
            detalles={},
            ejecutado_at=datetime.now(timezone.utc),
            puede_deshacer=False,
        )

    async def execute(
        self,
        accion: AccionPropuesta,
        contexto: Dict[str, Any],
    ) -> Dict[str, Any]:
        objetivo = (accion.objetivo or "").strip()
        incident_id = str(contexto.get("incident_id") or "")
        ejecutado_by = str(contexto.get("ejecutado_by") or "auto")

        can, why = await self.check_preconditions(objetivo)
        if not can:
            pr = PlaybookResult(
                execution_id="",
                playbook=self.nombre,
                objetivo=objetivo,
                exitoso=False,
                mensaje=why,
                detalles={"fase": "preconditions"},
                ejecutado_at=datetime.now(timezone.utc),
                puede_deshacer=False,
            )
            return playbook_result_to_audit_dict(pr)

        try:
            pr = await self.execute_core(objetivo, incident_id, ejecutado_by)
        except Exception as e:
            pr = PlaybookResult(
                execution_id="",
                playbook=self.nombre,
                objetivo=objetivo,
                exitoso=False,
                mensaje=str(e),
                detalles={"fase": "execute_core"},
                ejecutado_at=datetime.now(timezone.utc),
                puede_deshacer=False,
            )
        return playbook_result_to_audit_dict(pr)


# Alias historico
PlaybookBase = BasePlaybook
