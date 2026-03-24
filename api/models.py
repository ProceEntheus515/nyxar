import uuid
from datetime import datetime, timezone
from typing import Literal, Optional, List
from pydantic import BaseModel, Field, field_validator, ConfigDict, ValidationInfo

from api.validators import (
    USERNAME_PATTERN,
    normalize_domain_strip_port,
    validate_externo_hash,
    validate_externo_texto,
    validate_externo_url,
    validate_ip,
    validate_no_path_traversal,
)

# --- CONSTANTES Y FUNCIONES GLOBALES ---

RISK_SCORE_THRESHOLDS = {"critico": 80, "alto": 60, "medio": 40, "bajo": 20}

def get_severidad(risk_score: int) -> str:
    """Calcula la severidad de un incidente basada en su nivel de riesgo actual."""
    if risk_score >= RISK_SCORE_THRESHOLDS["critico"]:
        return "critica"
    elif risk_score >= RISK_SCORE_THRESHOLDS["alto"]:
        return "alta"
    elif risk_score >= RISK_SCORE_THRESHOLDS["medio"]:
        return "media"
    elif risk_score >= RISK_SCORE_THRESHOLDS["bajo"]:
        return "baja"
    return "info"

def generate_event_id() -> str:
    """Auto-genera un ID único inmutable para el Evento base."""
    timestamp_unix = int(datetime.now(timezone.utc).timestamp())
    random4 = uuid.uuid4().hex[:4]
    return f"evt_{timestamp_unix}_{random4}"

# --- MODELOS DE DOMINIO ---

class EventoInterno(BaseModel):
    ip: str
    hostname: str
    usuario: str
    area: str

    @field_validator("ip")
    @classmethod
    def validar_ip_interna(cls, v: str) -> str:
        return validate_ip(v)

    @field_validator("hostname", "usuario", "area")
    @classmethod
    def validar_texto_interno(cls, v: str) -> str:
        s = (v or "").strip()
        s = validate_no_path_traversal(s)
        if len(s) > 256:
            raise ValueError("Campo interno demasiado largo")
        return s


class EventoExterno(BaseModel):
    """tipo antes de valor para que el validador de valor conozca el tipo (Pydantic v2)."""

    tipo: Literal["ip", "dominio", "url", "hash", "texto"]
    valor: str

    @field_validator("valor")
    @classmethod
    def validar_valor_externo(cls, v: str, info: ValidationInfo) -> str:
        tipo = info.data.get("tipo")
        if tipo == "ip":
            return validate_ip(v)
        if tipo == "dominio":
            return normalize_domain_strip_port(v)
        if tipo == "hash":
            return validate_externo_hash(v)
        if tipo == "url":
            return validate_externo_url(v)
        if tipo == "texto":
            return validate_externo_texto(v, max_len=512)
        return v

class Enrichment(BaseModel):
    reputacion: Literal["limpio", "sospechoso", "malicioso", "desconocido"]
    fuente: str
    categoria: Optional[str] = None
    pais_origen: Optional[str] = None
    asn: Optional[str] = None
    registrado_hace_dias: Optional[int] = None
    virustotal_detecciones: Optional[str] = None
    tags: List[str] = Field(default_factory=list)

class Evento(BaseModel):
    id: str = Field(default_factory=generate_event_id)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source: Literal["dns", "proxy", "firewall", "wazuh", "endpoint"]
    tipo: Literal["query", "request", "block", "alert", "process"]
    interno: EventoInterno
    externo: EventoExterno
    enrichment: Optional[Enrichment] = None
    risk_score: Optional[int] = Field(default=None, ge=0, le=100)
    correlaciones: List[str] = Field(default_factory=list)

    @field_validator('timestamp')
    @classmethod
    def ensure_utc(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            v = v.replace(tzinfo=timezone.utc)
        return v

    def to_mongo_dict(self) -> dict:
        """Serializa de forma nativa manteniendo timestamp para MongoDB y transformando ID."""
        data = self.model_dump(exclude_none=True)
        data["_id"] = data.pop("id")
        return data

    def to_redis_dict(self) -> dict:
        """Serializa 100% JSON puro (datetimes a strings) para Redis streams/caché."""
        data = self.model_dump(mode="json", exclude_none=False)
        return data

    model_config = ConfigDict(
        frozen=True,
        json_schema_extra={
            "examples": [
                {
                    "source": "dns",
                    "tipo": "query",
                    "interno": {
                        "ip": "192.168.1.100",
                        "hostname": "marketing-pc",
                        "usuario": "jdoe",
                        "area": "Marketing"
                    },
                    "externo": {
                        "valor": "maliciousexample.com",
                        "tipo": "dominio"
                    }
                }
            ]
        }
    )

class BaselineData(BaseModel):
    horario_inicio: str
    horario_fin: str
    dias_laborales: List[str]
    dominios_habituales: List[str]
    volumen_mb_dia_media: float
    volumen_mb_dia_std: float
    servidores_internos: List[str]
    muestras_recolectadas: int = 0
    baseline_valido: bool = False

class Identidad(BaseModel):
    id: str
    usuario: str
    area: str
    dispositivo: str
    hostname: str
    baseline: Optional[BaselineData] = None
    risk_score_actual: int = 0
    ultima_actividad: Optional[datetime] = None

    @field_validator("usuario")
    @classmethod
    def validar_usuario_identidad(cls, v: str) -> str:
        s = (v or "").strip()
        if not USERNAME_PATTERN.match(s):
            raise ValueError(f"Username inválido: {v}")
        return s.lower()

    @field_validator("id", "area", "dispositivo", "hostname")
    @classmethod
    def validar_identidad_texto(cls, v: str) -> str:
        s = validate_no_path_traversal((v or "").strip())
        if len(s) > 256:
            raise ValueError("Campo de identidad demasiado largo")
        return s

class Incidente(BaseModel):
    id: str
    titulo: str
    descripcion: str
    severidad: Literal["critica", "alta", "media", "baja", "info"]
    eventos_ids: List[str]
    estado: Literal["abierto", "investigando", "cerrado", "falso_positivo"] = "abierto"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    closed_at: Optional[datetime] = None

class AiMemo(BaseModel):
    id: str
    tipo: Literal["autonomo", "incidente", "ceo", "hunting"]
    contenido: str
    prioridad: Literal["critica", "alta", "media", "info"]
    eventos_relacionados: List[str]
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class HoneypotHit(BaseModel):
    id: str
    recurso: str
    tipo_recurso: Literal["share", "ip_fantasma", "usuario_ad", "dns_interno", "archivo"]
    ip_interna: str
    usuario: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
