"""
Deteccion de proxy (D02): env, gateway+puertos comunes, logs locales.
Sin credenciales en el mapa; 407 implica proxy_auth_required (NTLM/LDAP, etc.).
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

from nyxar.discovery.engine import InfrastructureMap
from nyxar.discovery.netutil import get_default_gateway_sync

logger = logging.getLogger("nyxar.discovery.probes.proxy")

COMMON_PROXY_PORTS = [3128, 8080, 8888, 80, 3129, 8443]

COMMON_LOG_PATHS = [
    "/var/log/squid/access.log",
    "/var/log/squid3/access.log",
    "/usr/local/squid/var/logs/access.log",
    "/var/log/nginx/access.log",
    "/var/log/nginx/proxy.log",
    "/host/logs/squid/access.log",
    "/host/logs/nginx/access.log",
]


class ProxyProbe:
    def __init__(self, infra: InfrastructureMap) -> None:
        self.infra = infra

    async def run(self) -> None:
        try:
            await self._run_inner()
        except Exception as e:
            logger.debug("proxy probe: %s", e)

    async def _run_inner(self) -> None:
        # 1) Variables de entorno (cliente explicito hacia proxy)
        env_proxy = (
            os.environ.get("HTTP_PROXY")
            or os.environ.get("http_proxy")
            or os.environ.get("HTTPS_PROXY")
            or os.environ.get("https_proxy")
            or os.environ.get("ALL_PROXY")
            or os.environ.get("all_proxy")
        )
        if env_proxy and str(env_proxy).strip():
            self._parse_proxy_url(str(env_proxy).strip())
            self._apply_tls_bump_from_env()
            self._apply_explicit_log_path_from_env()
            return

        # 2) Puertos comunes en la gateway (p. ej. Squid transparente con admin en gateway)
        gateway = await asyncio.to_thread(get_default_gateway_sync)
        if gateway:
            for port in COMMON_PROXY_PORTS:
                proxy_type = await self._probe_proxy_port(gateway, port)
                if proxy_type:
                    self.infra.proxy_present = True
                    self.infra.proxy_host = gateway
                    self.infra.proxy_port = port
                    self.infra.proxy_type = proxy_type
                    break

        # 3) Logs locales (Squid transparente sin HTTP_PROXY en este host)
        await asyncio.to_thread(self._scan_log_paths)

        self._apply_tls_bump_from_env()
        self._apply_explicit_log_path_from_env()
        self._detect_cloud_proxy_from_env()

    def _parse_proxy_url(self, raw: str) -> None:
        parsed = urlparse(raw if "://" in raw else f"http://{raw}")
        host = parsed.hostname
        if not host:
            return
        port = parsed.port or (443 if parsed.scheme == "https" else 8080)
        self.infra.proxy_present = True
        self.infra.proxy_host = host
        self.infra.proxy_port = port
        self.infra.proxy_type = self._guess_type_from_scheme_host(host, port)
        if parsed.username or os.environ.get("HTTP_PROXY_USER"):
            self.infra.proxy_auth_required = True

    @staticmethod
    def _guess_type_from_scheme_host(host: str, port: int) -> str:
        h = host.lower()
        if "zscaler" in h:
            return "zscaler"
        if "netskope" in h:
            return "netskope"
        if "cloudflare" in h or "gateway" in h:
            return "cloudflare"
        if port in (3128, 3129):
            return "squid"
        return "other"

    def _apply_tls_bump_from_env(self) -> None:
        bump = (os.environ.get("NYXAR_PROXY_TLS_BUMP") or "").lower() in (
            "1",
            "true",
            "yes",
        )
        if bump:
            self.infra.proxy_tls_bump = True
            self.infra.tls_inspection = True

    def _apply_explicit_log_path_from_env(self) -> None:
        log_path = (os.environ.get("NYXAR_PROXY_LOG_PATH") or "").strip()
        if not log_path:
            return
        p = Path(log_path)
        if p.is_file() and os.access(p, os.R_OK):
            self.infra.proxy_log_path = str(p)
            self.infra.proxy_log_format = _detect_log_format(str(p))

    def _scan_log_paths(self) -> None:
        for log_path in COMMON_LOG_PATHS:
            p = Path(log_path)
            if p.is_file() and os.access(p, os.R_OK):
                self.infra.proxy_log_path = str(p)
                self.infra.proxy_log_format = _detect_log_format(str(p))
                if not self.infra.proxy_present:
                    self.infra.proxy_present = True
                    self.infra.proxy_type = "local_squid"
                break

    def _detect_cloud_proxy_from_env(self) -> None:
        """Logs en API cloud (Zscaler, Netskope, Cloudflare Gateway): solo metadata, sin tokens."""
        prov = (os.environ.get("NYXAR_PROXY_CLOUD_PROVIDER") or "").strip().lower()
        if prov in ("zscaler", "netskope", "cloudflare", "cloudflare_gateway"):
            self.infra.proxy_present = True
            if prov == "cloudflare_gateway":
                self.infra.proxy_type = "cloudflare"
            else:
                self.infra.proxy_type = prov
            fmt = (os.environ.get("NYXAR_PROXY_CLOUD_LOG_FORMAT") or "json").strip()
            self.infra.proxy_log_format = fmt or "json"

    async def _probe_proxy_port(self, host: str, port: int) -> Optional[str]:
        writer = None
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port),
                timeout=2.0,
            )
            writer.write(
                b"CONNECT example.com:443 HTTP/1.1\r\nHost: example.com:443\r\n\r\n"
            )
            await writer.drain()
            response = await asyncio.wait_for(reader.read(1024), timeout=2.0)
            response_str = response.decode("utf-8", errors="ignore")

            rs = response_str.lower()
            if "squid" in rs:
                return "squid"
            if "nginx" in rs:
                return "nginx"
            if "zscaler" in rs:
                return "zscaler"
            if "200 connection established" in rs:
                return "generic_proxy"
            if "407" in rs and "proxy-authenticate" in rs:
                self.infra.proxy_auth_required = True
                return "proxy_with_auth"
        except (asyncio.TimeoutError, ConnectionRefusedError, OSError):
            pass
        finally:
            if writer is not None:
                writer.close()
                try:
                    await writer.wait_closed()
                except OSError:
                    pass
        return None


def _detect_log_format(log_path: str) -> str:
    try:
        with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
            first_line = f.readline().strip()
        if not first_line:
            return "unknown"
        if first_line[0].isdigit() and "TCP_" in first_line:
            return "squid_native"
        if first_line[0].isdigit() and "[" in first_line:
            return "combined_log_format"
        if first_line.startswith("{"):
            return "json"
        return "unknown"
    except OSError:
        return "unknown"
