from __future__ import annotations

from typing import Any

from nyxar.discovery.engine import InfrastructureMap


def suggest_firewall_env(infra: InfrastructureMap) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if infra.firewall_type:
        out["NYXAR_FIREWALL_TYPE"] = infra.firewall_type
    if infra.syslog_port:
        out["NYXAR_SYSLOG_PORT"] = str(infra.syslog_port)
    if infra.syslog_protocol:
        out["NYXAR_SYSLOG_PROTOCOL"] = infra.syslog_protocol
    if infra.syslog_format:
        out["NYXAR_SYSLOG_FORMAT"] = infra.syslog_format
    return out
