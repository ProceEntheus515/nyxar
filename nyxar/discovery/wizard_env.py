"""
Bloque de variables sugeridas para el Setup Wizard (D08). Sin credenciales.
"""

from __future__ import annotations

from typing import Any

from nyxar.discovery.adapters.dns_adapter import suggest_dns_env
from nyxar.discovery.adapters.firewall_adapter import suggest_firewall_env
from nyxar.discovery.adapters.proxy_adapter import suggest_proxy_env
from nyxar.discovery.adapters.siem_adapter import suggest_siem_env
from nyxar.discovery.adapters.tls_adapter import suggest_tls_env
from nyxar.discovery.engine import InfrastructureMap


def merge_suggested_env(infra: InfrastructureMap) -> dict[str, str]:
    """Une sugerencias de adaptadores en un solo dict (valores string)."""
    merged: dict[str, str] = {}
    chunks: list[dict[str, Any]] = [
        suggest_dns_env(infra),
        suggest_proxy_env(infra),
        suggest_firewall_env(infra),
        suggest_tls_env(infra),
        suggest_siem_env(infra),
    ]
    for d in chunks:
        for k, v in d.items():
            if v is None:
                continue
            s = str(v).strip()
            if s:
                merged[k] = s
    if infra.network_range:
        merged["NETWORK_RANGE"] = infra.network_range.strip()
    merged["NYXAR_DISCOVERY_METHOD"] = "assisted"
    return dict(sorted(merged.items()))


def format_env_block(merged: dict[str, str]) -> str:
    """Texto listo para panel o archivo (solo variables no secretas del mapa)."""
    header = (
        "# NYXAR Setup Wizard — variables sugeridas (revisar antes de produccion).\n"
        "# Las credenciales van en la seccion inferior si las indicaste en el asistente.\n"
    )
    body = "\n".join(f"{k}={v}" for k, v in merged.items())
    return f"{header}\n{body}\n"
