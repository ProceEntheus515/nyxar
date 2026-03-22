"""Modelos Pydantic para planes de respuesta SOAR (propuesta humana en el bucle)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Literal, List

from pydantic import BaseModel, Field


class PlaybookResult(BaseModel):
    """Resultado estandarizado de un playbook (PROMPTS_V2)."""

    execution_id: str = ""
    playbook: str = ""
    objetivo: str = ""
    exitoso: bool = False
    mensaje: str = ""
    detalles: Dict[str, Any] = Field(default_factory=dict)
    ejecutado_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    puede_deshacer: bool = False


class AccionPropuesta(BaseModel):
    tipo: Literal["quarantine", "block_ip", "disable_user", "notify_only"]
    objetivo: str
    descripcion: str
    reversible: bool
    impacto: str
    requiere_aprobacion: bool = True


class ResponsePlan(BaseModel):
    incident_id: str
    playbook_nombre: str
    acciones: List[AccionPropuesta]
    justificacion: str
    urgencia: Literal["inmediata", "proxima_hora", "proximo_dia"] = Field(
        default="proxima_hora"
    )
