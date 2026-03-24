"""
Validación estricta de respuestas de APIs externas antes de enriquecer (S11).
No confiar en el formato ni en la buena fe del upstream.
"""

from __future__ import annotations

import json
import re
from typing import Any, Optional, Type

from pydantic import BaseModel, ConfigDict, Field, field_validator, ValidationError

from shared.logger import get_logger

logger = get_logger("enricher.validators.external")


class AbuseIPDBResponse(BaseModel):
    """Subconjunto validado del objeto `data` de AbuseIPDB v2 /check."""

    model_config = ConfigDict(extra="ignore")

    ipAddress: str
    isPublic: bool = True
    abuseConfidenceScore: int
    countryCode: Optional[str] = None
    isp: Optional[str] = None

    @field_validator("abuseConfidenceScore")
    @classmethod
    def validate_score(cls, v: int) -> int:
        if not 0 <= v <= 100:
            raise ValueError("abuseConfidenceScore fuera de rango")
        return v

    @field_validator("countryCode")
    @classmethod
    def validate_country(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == "":
            return v
        u = v.strip().upper()
        if not re.match(r"^[A-Z]{2}$", u):
            raise ValueError("countryCode invalido")
        return u


class OTXPulseInfoBlock(BaseModel):
    """Bloque pulse_info de OTX indicator general."""

    model_config = ConfigDict(extra="ignore")

    count: int = 0
    pulses: list[Any] = Field(default_factory=list)

    @field_validator("count")
    @classmethod
    def validate_count(cls, v: int) -> int:
        if v < 0 or v > 100_000:
            raise ValueError("pulse count fuera de rango")
        return v


class OTXGeneralResponse(BaseModel):
    """Cuerpo JSON de OTX /indicators/.../general usado por el enricher."""

    model_config = ConfigDict(extra="ignore")

    pulse_info: Optional[OTXPulseInfoBlock] = None
    base_indicator: Optional[dict[str, Any]] = None
    asn: Optional[str] = None


def _raw_snippet(raw: dict[str, Any], maxlen: int = 200) -> str:
    try:
        s = json.dumps(raw, default=str)
    except (TypeError, ValueError):
        s = str(raw)
    return s[:maxlen]


def validate_external_response(
    raw_response: dict[str, Any],
    expected_schema: Type[BaseModel],
    source_name: str,
) -> Optional[BaseModel]:
    """
    Parsea y valida contra el esquema. Si falla: log acotado y None.
    No loguear la respuesta completa (puede contener datos sensibles de terceros).
    """
    try:
        return expected_schema.model_validate(raw_response)
    except ValidationError as e:
        logger.warning(
            "Respuesta invalida de %s: %s. Muestra: %s",
            source_name,
            e,
            _raw_snippet(raw_response),
        )
        return None
