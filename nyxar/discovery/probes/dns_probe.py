"""
Deteccion DNS (D03): resolv.conf, tipo (Pi-hole, BIND, Unbound), rutas de log y API Pi-hole.
Sin credenciales en el mapa; cloud/Windows por variables de entorno opcionales.
"""

from __future__ import annotations

import asyncio
import logging
import os
import random
import socket
import ssl
import struct
import urllib.error
import urllib.request
from pathlib import Path
from typing import Optional

from nyxar.discovery.engine import InfrastructureMap
from nyxar.discovery.netutil import get_default_gateway_sync

logger = logging.getLogger("nyxar.discovery.probes.dns")


class DnsProbe:
    def __init__(self, infra: InfrastructureMap) -> None:
        self.infra = infra

    async def run(self) -> None:
        try:
            await self._run_inner()
        except Exception as e:
            logger.debug("dns probe: %s", e)

    async def _run_inner(self) -> None:
        dns_server = await self._get_system_dns()
        if dns_server:
            self.infra.dns_server = dns_server

        if self.infra.dns_server:
            dns_type = await self._identify_dns_type(self.infra.dns_server)
            self.infra.dns_type = dns_type
            await asyncio.to_thread(
                self._find_log_access, self.infra.dns_server, dns_type
            )
        else:
            await asyncio.to_thread(self._find_log_access, "", "unknown_dns")

        self._scan_pihole_paths()
        self._apply_dns_env_overrides()

        if self.infra.dns_server and (
            not self.infra.dns_type or self.infra.dns_type == "unknown_dns"
        ):
            self.infra.dns_type = "other"

    def _apply_dns_env_overrides(self) -> None:
        """Windows DNS, cloud corporativo (solo etiquetas; credenciales fuera del mapa)."""
        cloud = (os.environ.get("NYXAR_DNS_CLOUD_PROVIDER") or "").strip().lower()
        if cloud in ("cloudflare_gateway", "cisco_umbrella", "umbrella"):
            self.infra.dns_type = "cloud_dns"
            self.infra.dns_log_format = self.infra.dns_log_format or "json"
        t = (os.environ.get("NYXAR_DNS_TYPE") or "").strip().lower()
        if t in (
            "windows_dns",
            "bind9",
            "unbound",
            "pihole",
            "other",
            "cloud_dns",
        ):
            self.infra.dns_type = t
        api = (os.environ.get("PIHOLE_API_URL") or "").strip().rstrip("/")
        if api:
            self.infra.dns_api_url = api
            self.infra.dns_type = self.infra.dns_type or "pihole"
        custom = (os.environ.get("NYXAR_DNS_LOG_PATH") or "").strip()
        if custom:
            p = Path(custom)
            if p.is_file() and os.access(p, os.R_OK):
                self.infra.dns_log_path = str(p)
                self.infra.dns_log_format = self.infra.dns_log_format or _guess_dns_format_from_path(
                    p
                )

    async def _get_system_dns(self) -> Optional[str]:
        return await asyncio.to_thread(_read_system_dns_sync)

    async def _identify_dns_type(self, dns_server: str) -> str:
        forced = (os.environ.get("NYXAR_DNS_TYPE") or "").strip().lower()
        if forced in ("windows_dns", "bind9", "unbound", "pihole", "cloud_dns", "other"):
            return forced

        cloud = (os.environ.get("NYXAR_DNS_CLOUD_PROVIDER") or "").strip().lower()
        if cloud in ("cloudflare_gateway", "cisco_umbrella", "umbrella"):
            return "cloud_dns"

        api_base = await asyncio.to_thread(_discover_pihole_api_url, dns_server)
        if api_base:
            self.infra.dns_api_url = api_base
            return "pihole"

        version_blob = await asyncio.to_thread(_query_dns_chaos_version_bind, dns_server)
        if version_blob:
            low = version_blob.lower()
            if "bind" in low:
                return "bind9"
            if "unbound" in low:
                return "unbound"
            if "nsd" in low:
                return "other"

        return "unknown_dns"

    def _find_log_access(self, dns_server: str, dns_type: str) -> None:
        if dns_type == "pihole" and self.infra.dns_api_url:
            self.infra.dns_log_format = self.infra.dns_log_format or "pihole_api"

        if dns_type == "pihole":
            for path in (
                "/var/log/pihole.log",
                "/etc/pihole/pihole.log",
                "/var/log/pihole/pihole.log",
                "/logs/dns/pihole.log",
                "/host/logs/pihole/pihole.log",
                "/host/logs/pihole.log",
            ):
                p = Path(path)
                if p.is_file() and os.access(p, os.R_OK):
                    self.infra.dns_log_path = str(p)
                    self.infra.dns_log_format = "pihole"
                    break

        elif dns_type == "bind9":
            for path in (
                "/var/log/named/query.log",
                "/var/log/bind/query.log",
                "/var/log/named.log",
                "/var/log/syslog",
                "/host/logs/syslog",
            ):
                p = Path(path)
                if p.is_file() and os.access(p, os.R_OK):
                    self.infra.dns_log_path = str(p)
                    self.infra.dns_log_format = "bind_query"
                    break

        elif dns_type == "unbound":
            for path in (
                "/var/log/unbound/unbound.log",
                "/var/log/unbound.log",
                "/host/logs/unbound.log",
            ):
                p = Path(path)
                if p.is_file() and os.access(p, os.R_OK):
                    self.infra.dns_log_path = str(p)
                    self.infra.dns_log_format = "unbound"
                    break

        elif dns_type == "windows_dns":
            self.infra.dns_log_format = self.infra.dns_log_format or "windows_dns_event"

    def _scan_pihole_paths(self) -> None:
        if self.infra.dns_log_path:
            return
        candidates = [
            Path("/logs/dns/pihole.log"),
            Path("/var/log/pihole/pihole.log"),
            Path("/var/log/pihole.log"),
            Path("/host/logs/pihole/pihole.log"),
            Path("/host/logs/pihole.log"),
        ]
        for p in candidates:
            if p.is_file():
                self.infra.dns_log_path = str(p)
                self.infra.dns_log_format = "pihole"
                self.infra.dns_type = self.infra.dns_type or "pihole"
                break


def _guess_dns_format_from_path(p: Path) -> str:
    name = p.name.lower()
    parent = str(p).lower()
    if "pihole" in parent or "dnsmasq" in parent:
        return "pihole"
    if "named" in parent or "bind" in parent:
        return "bind_query"
    if "unbound" in parent:
        return "unbound"
    if name == "syslog":
        return "bind_query"
    return "pihole"


def _read_system_dns_sync() -> Optional[str]:
    resolv = Path("/etc/resolv.conf")
    if not resolv.is_file():
        return get_default_gateway_sync()

    ips: list[str] = []
    try:
        for line in resolv.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line.startswith("nameserver "):
                continue
            parts = line.split()
            if len(parts) >= 2:
                ips.append(parts[1].strip())
    except OSError:
        return get_default_gateway_sync()

    for ip in ips:
        if not ip.startswith("127."):
            return ip
    if ips:
        return ips[0]
    return get_default_gateway_sync()


def _discover_pihole_api_url(dns_server: str) -> Optional[str]:
    """Devuelve URL base tipo http://host/admin/api.php si responde como Pi-hole."""
    bases = [
        f"http://{dns_server}/admin/api.php",
        "http://pihole.local/admin/api.php",
        "http://pi.hole/admin/api.php",
    ]
    insecure = ssl.create_default_context()
    insecure.check_hostname = False
    insecure.verify_mode = ssl.CERT_NONE

    for base in bases:
        base = base.rstrip("/")
        if not base.endswith("api.php"):
            continue
        url_http = f"{base}?summary"
        if _http_body_has_pihole_summary(url_http, None):
            return base
        url_https = url_http.replace("http://", "https://", 1)
        if _http_body_has_pihole_summary(url_https, insecure):
            return base.replace("http://", "https://", 1)
    return None


def _http_body_has_pihole_summary(
    url: str, ssl_ctx: Optional[ssl.SSLContext]
) -> bool:
    try:
        req = urllib.request.Request(url, method="GET")
        kwargs: dict = {"timeout": 3}
        if ssl_ctx is not None and url.lower().startswith("https"):
            kwargs["context"] = ssl_ctx
        with urllib.request.urlopen(req, **kwargs) as resp:
            body = resp.read(12000).decode("utf-8", errors="replace")
        return "dns_queries_today" in body or "domains_being_blocked" in body
    except (urllib.error.URLError, OSError, ValueError):
        return False


def _query_dns_chaos_version_bind(server: str) -> Optional[str]:
    """Consulta version.bind TXT CH (CHAOS); respuesta cruda para heuristica."""
    tid = random.randint(1, 65535)
    header = struct.pack("!HHHHHH", tid, 0x0100, 1, 0, 0, 0)
    qname = b"\x07version\x04bind\x00"
    question = qname + struct.pack("!HH", 16, 3)
    packet = header + question

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.settimeout(2.0)
        sock.sendto(packet, (server, 53))
        data, _ = sock.recvfrom(4096)
    except OSError:
        return None
    finally:
        sock.close()

    if not data or len(data) < 12:
        return None
    return data.decode("latin-1", errors="replace")
