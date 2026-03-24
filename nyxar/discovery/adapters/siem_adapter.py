from __future__ import annotations

from typing import Any

from nyxar.discovery.engine import InfrastructureMap


def suggest_siem_env(infra: InfrastructureMap) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if infra.siem_ingest_url:
        if infra.siem_type == "splunk":
            out["SPLUNK_HEC_URL"] = infra.siem_ingest_url
        elif infra.siem_type == "elastic":
            out["ELASTICSEARCH_URL"] = infra.siem_ingest_url
        else:
            out["NYXAR_SIEM_INGEST_URL"] = infra.siem_ingest_url
    return out
