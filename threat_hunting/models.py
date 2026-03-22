from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


class HuntingContext(BaseModel):
    """
    Resumen estructurado de la red para alimentar al LLM.
    Los campos se serializan a texto en el motor; no ejecutan queries.
    """

    estadisticas_24h: dict[str, Any] = Field(default_factory=dict)
    incidentes_semana: list[dict[str, Any]] = Field(default_factory=list)
    threat_intel_resumen: str = ""
    iocs_sin_alerta: list[dict[str, Any]] = Field(default_factory=list)
    identidades_riesgo_suave: list[dict[str, Any]] = Field(default_factory=list)


class Hypothesis(BaseModel):
    id: str = Field(default_factory=lambda: f"hyp_{uuid4().hex[:12]}")
    titulo: str
    descripcion: str
    tecnica_mitre: str = ""
    prioridad: int = Field(ge=1, le=5, default=3)
    queries_sugeridas: list[str] = Field(default_factory=list)
    estado: Literal["nueva", "investigando", "confirmada", "descartada"] = "nueva"
    creada_at: datetime = Field(default_factory=_now_utc)
    hunter: str = "claude_autonomo"


class HuntConclusion(BaseModel):
    hypothesis_id: str
    encontrado: bool
    evidencia: list[dict[str, Any]] = Field(default_factory=list)
    confianza: Literal["alta", "media", "baja"] = "baja"
    iocs_nuevos: list[str] = Field(default_factory=list)
    crear_incidente: bool = False
    resumen: str = ""
