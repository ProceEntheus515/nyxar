"""
Adaptador de lineas de log DNS al dict normalizado NYXAR (D03).
"""

from __future__ import annotations

import json
import re
from typing import Any, Callable, Optional

from nyxar.discovery.engine import InfrastructureMap

# dnsmasq / Pi-hole archivo: query[A] fqdn from 192.168.1.1
PIHOLE_LINE = re.compile(
    r"query\[([^\]]+)\]\s+(\S+)\s+from\s+(\S+)", re.IGNORECASE
)
# BIND query log
BIND_QUERY = re.compile(
    r"client\s+([0-9a-fA-F.:]+)#\d+:\s+query:\s+(\S+)\s+IN\s+(\S+)",
    re.IGNORECASE,
)
# Unbound (heuristico)
UNBOUND_QUERY = re.compile(
    r".*?query:\s+(\S+)\s+IN\s+(\S+).*?from\s+([0-9a-fA-F.:]+)",
    re.IGNORECASE,
)
# Windows DNS (texto de evento / Wazuh): busca FQDN e IP
WIN_DNS = re.compile(
    r"(?:Query|consulta).*?(?:for|para)\s+(\S+).*?(\d{1,3}(?:\.\d{1,3}){3})",
    re.IGNORECASE,
)


class DnsAdapter:
    """
    Normaliza lineas de Pi-hole/dnsmasq, BIND, Unbound, JSON API y texto tipo Windows Event.
    """

    def __init__(self, infra: InfrastructureMap) -> None:
        self.infra = infra
        self._parser: Optional[Callable[[str], Optional[dict[str, Any]]]] = None
        self._select_parser()

    def _select_parser(self) -> None:
        fmt = (self.infra.dns_log_format or "unknown").lower()
        mapping: dict[str, Callable[[str], Optional[dict[str, Any]]]] = {
            "pihole": self._parse_pihole_line,
            "syslog": self._parse_pihole_line,
            "bind_query": self._parse_bind_query,
            "unbound": self._parse_unbound,
            "pihole_api": self._parse_pihole_api_json,
            "windows_dns_event": self._parse_windows_dns,
            "json": self._parse_pihole_api_json,
        }
        self._parser = mapping.get(fmt, self._parse_best_effort)

    def parse_line(self, line: str) -> Optional[dict[str, Any]]:
        if not self._parser:
            return None
        line = line.strip()
        if not line:
            return None
        return self._parser(line)

    def _parse_pihole_line(self, line: str) -> Optional[dict[str, Any]]:
        m = PIHOLE_LINE.search(line)
        if not m:
            return self._parse_best_effort(line)
        return {
            "query_type": m.group(1),
            "domain": m.group(2),
            "client": m.group(3),
            "source": "pihole",
        }

    def _parse_bind_query(self, line: str) -> Optional[dict[str, Any]]:
        m = BIND_QUERY.search(line)
        if not m:
            return self._parse_best_effort(line)
        return {
            "client": m.group(1),
            "domain": m.group(2),
            "query_type": m.group(3),
            "source": "bind9",
        }

    def _parse_unbound(self, line: str) -> Optional[dict[str, Any]]:
        m = UNBOUND_QUERY.search(line)
        if not m:
            return self._parse_best_effort(line)
        return {
            "domain": m.group(1),
            "query_type": m.group(2),
            "client": m.group(3),
            "source": "unbound",
        }

    def _parse_pihole_api_json(self, line: str) -> Optional[dict[str, Any]]:
        if not line.startswith("{"):
            return None
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            return None
        return {
            "domains_being_blocked": data.get("domains_being_blocked"),
            "dns_queries_today": data.get("dns_queries_today"),
            "source": "pihole_api",
            "_raw": data,
        }

    def _parse_windows_dns(self, line: str) -> Optional[dict[str, Any]]:
        m = WIN_DNS.search(line)
        if not m:
            return self._parse_best_effort(line)
        return {
            "domain": m.group(1),
            "client": m.group(2),
            "source": "windows_dns",
        }

    def _parse_best_effort(self, line: str) -> Optional[dict[str, Any]]:
        dom = re.search(
            r"\b([a-z0-9](?:[a-z0-9-]*[a-z0-9])?(?:\.[a-z0-9-]+)+)\b",
            line,
            re.I,
        )
        ip = re.search(r"\b(\d{1,3}(?:\.\d{1,3}){3})\b", line)
        if not dom and not ip:
            return None
        return {
            "domain": dom.group(1) if dom else None,
            "client": ip.group(1) if ip else None,
            "_parse_quality": "best_effort",
        }


def suggest_dns_env(infra: InfrastructureMap) -> dict[str, Any]:
    """Variables sugeridas para collector/enriquecedor (sin tokens de API cloud)."""
    out: dict[str, Any] = {}
    if infra.dns_log_path:
        out["NYXAR_DNS_LOG_PATH"] = infra.dns_log_path
    if infra.dns_api_url:
        out["PIHOLE_API_URL"] = infra.dns_api_url
    if infra.dns_type:
        out["NYXAR_DNS_TYPE"] = infra.dns_type
    if infra.dns_log_format:
        out["NYXAR_DNS_LOG_FORMAT"] = infra.dns_log_format
    if infra.dns_server:
        out["NYXAR_DNS_SERVER"] = infra.dns_server
    return out
