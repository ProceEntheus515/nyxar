from __future__ import annotations

from typing import Any

from nyxar.discovery.engine import InfrastructureMap


def suggest_tls_env(infra: InfrastructureMap) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if infra.ca_cert_path:
        out["REQUESTS_CA_BUNDLE"] = infra.ca_cert_path
        out["SSL_CERT_FILE"] = infra.ca_cert_path
    return out
