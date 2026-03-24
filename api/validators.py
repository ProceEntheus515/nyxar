"""
Validación estricta de inputs (PROMPTS_V6 S03).
NYXAR no confía en datos externos sin validar.
"""

from __future__ import annotations

import re
import ipaddress
from typing import Any, Optional

# --- Patrones permitidos ---

DOMAIN_PATTERN = re.compile(
    r"^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$"
)

USERNAME_PATTERN = re.compile(r"^[a-zA-Z0-9._-]{1,64}$")

# Producción: evt_<unix>_<hex4>. Lab: evt_test_<unix>_<hex4>
EVENT_ID_PATTERN = re.compile(r"^evt_(?:test_)?[0-9]+_[a-fA-F0-9]{4}$")

VALID_EVENT_SOURCES = frozenset({"dns", "proxy", "firewall", "wazuh", "endpoint"})

FORBIDDEN_QUERY_OPERATORS = frozenset({"$where", "$expr", "$function"})


def validate_ip(value: str) -> str:
    """IPv4 o IPv6 válida."""
    try:
        ipaddress.ip_address(value.strip())
    except ValueError as e:
        raise ValueError(f"IP inválida: {value}") from e
    return value.strip()


def validate_domain(value: str) -> str:
    """Dominio RFC 1123; sin puerto ni path."""
    v = (value or "").strip()
    if not v or len(v) > 253:
        raise ValueError("Dominio inválido: longitud incorrecta")
    if ":" in v:
        raise ValueError(f"Dominio no puede contener puerto: {value}")
    if not DOMAIN_PATTERN.match(v):
        raise ValueError(f"Dominio con formato inválido: {value}")
    return v.lower()


def normalize_domain_strip_port(value: str) -> str:
    """
    Quita sufijo :puerto cuando es numérico (p. ej. host desde proxy malformado)
    y valida como dominio.
    """
    v = (value or "").strip()
    if ":" in v and v.count(":") == 1:
        host, _, port = v.partition(":")
        if port.isdigit() and host:
            v = host.strip()
    return validate_domain(v)


def validate_event_source(value: str) -> str:
    s = (value or "").strip().lower()
    if s not in VALID_EVENT_SOURCES:
        raise ValueError(f"Fuente desconocida: {value}")
    return s


def sanitize_for_prompt(value: str, max_length: int = 200) -> str:
    """Limpia texto antes de enviarlo a prompts de IA (S04 amplía prompt injection)."""
    sanitized = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", value or "")
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length] + "..."
    return sanitized


def validate_no_path_traversal(value: str) -> str:
    """Evita secuencias típicas de path traversal en strings que puedan usarse como path."""
    v = value or ""
    dangerous = ("../", "..\\", "/etc/", "/proc/", "~", "%2e%2e")
    lower = v.lower()
    for pattern in dangerous:
        if pattern in lower:
            raise ValueError(f"Intento de path traversal detectado: {value}")
    return v


def validate_mongodb_query(query: dict[str, Any]) -> dict[str, Any]:
    """Rechaza operadores Mongo peligrosos en dicts controlados por el usuario."""

    def check_obj(obj: Any, depth: int) -> None:
        if depth > 10:
            raise ValueError("Query demasiado profunda")
        if isinstance(obj, dict):
            for key, val in obj.items():
                if key in FORBIDDEN_QUERY_OPERATORS:
                    raise ValueError(f"Operador MongoDB prohibido: {key}")
                check_obj(val, depth + 1)
        elif isinstance(obj, list):
            for item in obj:
                check_obj(item, depth + 1)

    check_obj(query, 0)
    return query


def validate_event_id_param(value: str) -> str:
    """ID de evento en rutas o query (formato NYXAR)."""
    v = (value or "").strip()
    if not EVENT_ID_PATTERN.match(v):
        raise ValueError(f"ID de evento inválido: {value}")
    return v


def validate_externo_hash(value: str) -> str:
    v = (value or "").strip()
    if not re.match(r"^[a-fA-F0-9]{32,64}$", v):
        raise ValueError(f"Hash inválido: {value}")
    return v.lower()


def validate_externo_url(value: str) -> str:
    v = value or ""
    if len(v) > 2000 or "\x00" in v:
        raise ValueError("URL inválida")
    validate_no_path_traversal(v)
    return v


def validate_externo_texto(value: str, max_len: int = 512) -> str:
    """Texto libre no DNS (p. ej. descripción de regla Wazuh, nombre de proceso)."""
    s = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", value or "")
    s = validate_no_path_traversal(s.strip())
    if len(s) > max_len:
        raise ValueError("Texto externo demasiado largo")
    return s


def validate_iso_timestamp_bound(value: Optional[str]) -> Optional[str]:
    """Límites seguros para filtros timestamp en query (evita inyección en string match)."""
    if value is None:
        return None
    v = value.strip()
    if not v:
        return None
    if len(v) > 48 or "\x00" in v or "$" in v:
        raise ValueError("Parámetro de fecha inválido")
    return v


def validate_area_query(value: Optional[str]) -> Optional[str]:
    """Área alfanumérica + guiones/underscore (query params)."""
    if value is None:
        return None
    v = value.strip()
    if not v:
        return None
    if len(v) > 50 or not re.match(r"^[a-zA-Z0-9_-]+$", v):
        raise ValueError("Área inválida")
    return v


def validate_resource_path_id(value: str, *, max_len: int = 200) -> str:
    """IDs en path (incidentes, identidades, etc.): sin traversal y longitud acotada."""
    v = validate_no_path_traversal((value or "").strip())
    if not v or len(v) > max_len:
        raise ValueError("Identificador inválido")
    return v
