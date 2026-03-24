from __future__ import annotations

from typing import Any

from nyxar.discovery.engine import InfrastructureMap


def suggest_dns_env(infra: InfrastructureMap) -> dict[str, Any]:
    """Variables sugeridas para collector/enriquecedor (sin tokens)."""
    out: dict[str, Any] = {}
    if infra.dns_log_path:
        out["NYXAR_DNS_LOG_PATH"] = infra.dns_log_path
    if infra.dns_api_url:
        out["PIHOLE_API_URL"] = infra.dns_api_url
    return out
