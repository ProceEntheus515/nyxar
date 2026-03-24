"""
Adaptador de lineas de log de proxy al dict normalizado NYXAR (D02).
"""

from __future__ import annotations

import json
import re
from typing import Any, Callable, Optional

from nyxar.discovery.engine import InfrastructureMap

CLF_PATTERN = re.compile(
    r'(\S+) \S+ \S+ \[([^\]]+)\] "(\S+) (\S+) \S+" (\d+) (\d+|-)'
)


class ProxyAdapter:
    """
    Unifica parseo de logs (Squid, nginx/CLF, JSON cloud) hacia un dict estable.
    """

    def __init__(self, infra: InfrastructureMap) -> None:
        self.infra = infra
        self._parser: Optional[Callable[[str], Optional[dict[str, Any]]]] = None
        self._select_parser()

    def _select_parser(self) -> None:
        if not self.infra.proxy_present and not self.infra.proxy_log_path:
            self._parser = None
            return

        format_to_parser: dict[str, Callable[[str], Optional[dict[str, Any]]]] = {
            "squid_native": self._parse_squid_native,
            "combined_log_format": self._parse_clf,
            "clf": self._parse_clf,
            "json": self._parse_json_log,
            "unknown": self._parse_best_effort,
        }
        fmt = self.infra.proxy_log_format or "unknown"
        self._parser = format_to_parser.get(fmt, self._parse_best_effort)

    def parse_line(self, line: str) -> Optional[dict[str, Any]]:
        if not self._parser:
            return None
        line = line.strip()
        if not line:
            return None
        return self._parser(line)

    def _parse_squid_native(self, line: str) -> Optional[dict[str, Any]]:
        """
        timestamp elapsed client action/code bytes method url
        Ej: 1742400000.000  42 192.168.1.45 TCP_MISS/200 8523 GET http://example.com/
        """
        parts = line.split()
        if len(parts) < 7:
            return None
        try:
            action_part = parts[3]
            if "/" not in action_part:
                return None
            action, code_s = action_part.split("/", 1)
            status_code = int(code_s)
            return {
                "timestamp": float(parts[0]),
                "client": parts[2],
                "action": action,
                "status_code": status_code,
                "bytes": int(parts[4]),
                "method": parts[5],
                "url": parts[6],
            }
        except (ValueError, IndexError):
            return None

    def _parse_clf(self, line: str) -> Optional[dict[str, Any]]:
        match = CLF_PATTERN.match(line)
        if not match:
            return None
        bytes_s = match.group(6)
        bytes_val = 0 if bytes_s == "-" else int(bytes_s)
        return {
            "client": match.group(1),
            "timestamp": match.group(2),
            "method": match.group(3),
            "url": match.group(4),
            "status_code": int(match.group(5)),
            "bytes": bytes_val,
        }

    def _parse_json_log(self, line: str) -> Optional[dict[str, Any]]:
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            return None
        status = data.get("status") or data.get("responsecode")
        try:
            status_code = int(status) if status is not None else None
        except (TypeError, ValueError):
            status_code = None
        bytes_v = data.get("bytes") or data.get("totalsize")
        try:
            bytes_int = int(bytes_v) if bytes_v is not None else None
        except (TypeError, ValueError):
            bytes_int = None
        return {
            "timestamp": data.get("timestamp")
            or data.get("time")
            or data.get("ts"),
            "client": data.get("clientip") or data.get("src_ip") or data.get("user"),
            "url": data.get("url") or data.get("destination"),
            "method": data.get("method") or data.get("requestmethod"),
            "status_code": status_code,
            "bytes": bytes_int,
            "_raw": data,
        }

    def _parse_best_effort(self, line: str) -> Optional[dict[str, Any]]:
        ip_match = re.search(r"\b(\d{1,3}\.){3}\d{1,3}\b", line)
        url_match = re.search(r"https?://\S+", line)
        if not ip_match and not url_match:
            return None
        return {
            "client": ip_match.group(0) if ip_match else None,
            "url": url_match.group(0) if url_match else None,
            "_parse_quality": "best_effort",
        }


def suggest_proxy_env(infra: InfrastructureMap) -> dict[str, Any]:
    """Sugerencias de entorno para el pipeline (sin passwords ni tokens)."""
    out: dict[str, Any] = {}
    if infra.proxy_host and infra.proxy_present:
        port = infra.proxy_port or 8080
        scheme = "https" if port in (443, 8443) else "http"
        out["HTTP_PROXY"] = f"{scheme}://{infra.proxy_host}:{port}"
        out["HTTPS_PROXY"] = out["HTTP_PROXY"]
    if infra.proxy_tls_bump:
        out["NYXAR_PROXY_TLS_BUMP"] = "true"
    if infra.proxy_log_path:
        out["NYXAR_PROXY_LOG_PATH"] = infra.proxy_log_path
    if infra.proxy_log_format:
        out["NYXAR_PROXY_LOG_FORMAT"] = infra.proxy_log_format
    if infra.proxy_type in ("zscaler", "netskope", "cloudflare"):
        out["NYXAR_PROXY_CLOUD_PROVIDER"] = infra.proxy_type
    return out
