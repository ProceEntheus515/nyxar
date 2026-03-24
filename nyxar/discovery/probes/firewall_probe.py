from __future__ import annotations

import logging
import os
import re
from pathlib import Path

from nyxar.discovery.engine import InfrastructureMap

logger = logging.getLogger("nyxar.discovery.probes.firewall")


class FirewallProbe:
    def __init__(self, infra: InfrastructureMap) -> None:
        self.infra = infra

    async def run(self) -> None:
        try:
            self._from_env_and_files()
        except Exception as e:
            logger.debug("firewall probe: %s", e)

    def _from_env_and_files(self) -> None:
        port_s = (os.environ.get("NYXAR_SYSLOG_PORT") or "").strip()
        if port_s.isdigit():
            self.infra.syslog_port = int(port_s)
            self.infra.firewall_present = True

        proto = (os.environ.get("NYXAR_SYSLOG_PROTOCOL") or "udp").strip().lower()
        if proto in ("udp", "tcp", "tls"):
            self.infra.syslog_protocol = proto

        fmt = (os.environ.get("NYXAR_SYSLOG_FORMAT") or "").strip()
        if fmt:
            self.infra.syslog_format = fmt

        fw_type = (os.environ.get("NYXAR_FIREWALL_TYPE") or "").strip()
        if fw_type:
            self.infra.firewall_type = fw_type
            self.infra.firewall_present = True

        for path in (Path("/etc/rsyslog.conf"), Path("/etc/syslog-ng/syslog-ng.conf")):
            if not path.is_file():
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            if re.search(r"514|syslog", text, re.I):
                self.infra.syslog_port = self.infra.syslog_port or 514
                self.infra.firewall_present = self.infra.firewall_present or bool(
                    self.infra.syslog_port
                )
            break
