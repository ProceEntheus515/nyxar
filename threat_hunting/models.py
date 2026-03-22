from datetime import datetime, timezone
from typing import Any, Literal, Optional
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


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
    model_config = ConfigDict(extra="ignore")

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


class MongoQuery(BaseModel):
    """Pipeline de agregación validado contra una colección permitida."""

    collection: str
    pipeline: list[dict[str, Any]]


class HuntQueryAudit(BaseModel):
    """Registro de una query ejecutada (auditoría)."""

    collection: str
    pipeline: list[dict[str, Any]]
    ok: bool
    resultado_count: int = 0
    error_o_timeout: str = ""
    muestra: list[dict[str, Any]] = Field(default_factory=list)


class HuntSession(BaseModel):
    id: str = Field(default_factory=lambda: f"hunt_{uuid4().hex[:12]}")
    hypothesis_id: str
    inicio: datetime = Field(default_factory=_now_utc)
    fin: Optional[datetime] = None
    estado: Literal["corriendo", "completado", "timeout", "error"] = "corriendo"
    queries_ejecutadas: int = 0
    resultados_totales: int = 0
    conclusion: Optional[HuntConclusion] = None
    iniciado_by: str = "sistema_autonomo"
    detalle_queries: list[HuntQueryAudit] = Field(default_factory=list)
    mensaje_error: str = ""


def hypothesis_from_mongo(doc: dict) -> Hypothesis:
    """Reconstruye Hypothesis desde un documento guardado en hunting_hypotheses."""
    d = {k: v for k, v in doc.items() if k not in ("_id", "titulo_normalizado")}
    ca = d.get("creada_at")
    if isinstance(ca, str):
        d["creada_at"] = datetime.fromisoformat(ca.replace("Z", "+00:00"))
    return Hypothesis.model_validate(d)
