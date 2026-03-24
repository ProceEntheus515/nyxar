"""
Sondeo SIEM (D06): variables de entorno y puertos tipicos en la gateway.
Sin tokens en el mapa; solo URLs base detectadas.
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
from nyxar.discovery.engine import InfrastructureMap
from nyxar.discovery.netutil import get_default_gateway_sync

logger = logging.getLogger("nyxar.discovery.probes.siem")

# (puerto, siem_type, rol: api|hec|web|kibana)
KNOWN_SIEM_PORTS: tuple[tuple[int, str, str], ...] = (
    (8089, "splunk", "api"),
    (8088, "splunk", "hec"),
    (8000, "splunk", "web"),
    (9200, "elastic", "api"),
    (5601, "elastic", "kibana"),
    (8413, "qradar", "api"),
)


class SiemProbe:
    def __init__(self, infra: InfrastructureMap) -> None:
        self.infra = infra

    async def run(self) -> None:
        try:
            self._from_env()
            if not self.infra.siem_present:
                await self._probe_gateway_ports()
        except Exception as e:
            logger.debug("siem probe: %s", e)

    def _from_env(self) -> None:
        splunk = (os.environ.get("SPLUNK_HEC_URL") or "").strip()
        if splunk and not self._looks_secret(splunk):
            self.infra.siem_present = True
            self.infra.siem_type = "splunk"
            self.infra.siem_ingest_url = splunk
            return

        splunk_mgmt = (os.environ.get("SPLUNK_MGMT_URL") or "").strip()
        if splunk_mgmt and not self._looks_secret(splunk_mgmt):
            self.infra.siem_present = True
            self.infra.siem_type = "splunk"
            self.infra.siem_api_url = splunk_mgmt.rstrip("/")
            return

        elastic = (
            os.environ.get("ELASTICSEARCH_URL")
            or os.environ.get("ELASTIC_URL")
            or ""
        ).strip()
        if elastic and not self._looks_secret(elastic):
            self.infra.siem_present = True
            self.infra.siem_type = "elastic"
            self.infra.siem_ingest_url = elastic
            self.infra.siem_api_url = elastic.rstrip("/")
            return

        qradar = (os.environ.get("QRADAR_CONSOLE_URL") or "").strip()
        if qradar:
            self.infra.siem_present = True
            self.infra.siem_type = "qradar"
            self.infra.siem_ingest_url = qradar
            self.infra.siem_api_url = qradar.rstrip("/")
            return

        generic = (os.environ.get("NYXAR_SIEM_INGEST_URL") or "").strip()
        if generic and not self._looks_secret(generic):
            self.infra.siem_present = True
            self.infra.siem_type = self.infra.siem_type or "other"
            self.infra.siem_ingest_url = generic

    async def _probe_gateway_ports(self) -> None:
        gw = await asyncio.to_thread(get_default_gateway_sync)
        if not gw:
            return
        for port, kind, role in KNOWN_SIEM_PORTS:
            if not await _tcp_port_open(gw, port):
                continue
            self.infra.siem_present = True
            self.infra.siem_type = kind
            base = f"https://{gw}:{port}"
            if kind == "splunk":
                if role == "hec":
                    self.infra.siem_ingest_url = f"{base}/services/collector/event"
                elif role == "api":
                    self.infra.siem_api_url = base
                else:
                    self.infra.siem_api_url = base
            elif kind == "elastic":
                if role == "api":
                    self.infra.siem_api_url = base
                else:
                    self.infra.siem_api_url = base
            elif kind == "qradar":
                self.infra.siem_api_url = base
            logger.info("SIEM detectado: %s (%s) en %s:%s", kind, role, gw, port)
            break

    @staticmethod
    def _looks_secret(url: str) -> bool:
        lower = url.lower()
        if re.search(r"token=|apikey=|api_key=|secret=", lower):
            return True
        return False


async def _tcp_port_open(host: str, port: int, timeout: float = 2.0) -> bool:
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port),
            timeout=timeout,
        )
        writer.close()
        try:
            await writer.wait_closed()
        except OSError:
            pass
        return True
    except (asyncio.TimeoutError, OSError, ConnectionRefusedError):
        return False
