from __future__ import annotations

import logging
import os
from pathlib import Path

from nyxar.discovery.engine import InfrastructureMap

logger = logging.getLogger("nyxar.discovery.probes.dns")


class DnsProbe:
    def __init__(self, infra: InfrastructureMap) -> None:
        self.infra = infra

    async def run(self) -> None:
        try:
            await self._detect()
        except Exception as e:
            logger.debug("dns probe: %s", e)

    async def _detect(self) -> None:
        resolv = Path("/etc/resolv.conf")
        if resolv.is_file():
            for line in resolv.read_text(encoding="utf-8", errors="replace").splitlines():
                line = line.strip()
                if line.startswith("nameserver ") and not line.startswith("nameserver 127"):
                    parts = line.split()
                    if len(parts) >= 2:
                        self.infra.dns_server = parts[1]
                        break

        custom = (os.environ.get("NYXAR_DNS_LOG_PATH") or "").strip()
        candidates = [
            Path(custom) if custom else None,
            Path("/logs/dns/pihole.log"),
            Path("/var/log/pihole/pihole.log"),
            Path("/var/log/pihole.log"),
            Path("/host/logs/pihole/pihole.log"),
            Path("/host/logs/pihole.log"),
        ]
        for p in candidates:
            if p is None:
                continue
            if p.is_file():
                self.infra.dns_log_path = str(p)
                self.infra.dns_log_format = "pihole"
                self.infra.dns_type = self.infra.dns_type or "pihole"
                break

        api = (os.environ.get("PIHOLE_API_URL") or "").strip().rstrip("/")
        if api:
            self.infra.dns_api_url = api
            self.infra.dns_type = self.infra.dns_type or "pihole"

        if self.infra.dns_server and not self.infra.dns_type:
            self.infra.dns_type = "other"
