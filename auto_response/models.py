"""Modelos Pydantic para planes de respuesta SOAR (propuesta humana en el bucle)."""

from __future__ import annotations

from typing import Literal, List

from pydantic import BaseModel, Field


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
