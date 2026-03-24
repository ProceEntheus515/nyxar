from __future__ import annotations

import logging
import os
import re

from nyxar.discovery.engine import InfrastructureMap

logger = logging.getLogger("nyxar.discovery.probes.siem")


class SiemProbe:
    def __init__(self, infra: InfrastructureMap) -> None:
        self.infra = infra

    async def run(self) -> None:
        try:
            self._from_env()
        except Exception as e:
            logger.debug("siem probe: %s", e)

    def _from_env(self) -> None:
        splunk = (os.environ.get("SPLUNK_HEC_URL") or "").strip()
        if splunk and not self._looks_secret(splunk):
            self.infra.siem_present = True
            self.infra.siem_type = "splunk"
            self.infra.siem_ingest_url = splunk
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
            return

        qradar = (os.environ.get("QRADAR_CONSOLE_URL") or "").strip()
        if qradar:
            self.infra.siem_present = True
            self.infra.siem_type = "qradar"
            self.infra.siem_ingest_url = qradar

        generic = (os.environ.get("NYXAR_SIEM_INGEST_URL") or "").strip()
        if generic and not self._looks_secret(generic):
            self.infra.siem_present = True
            self.infra.siem_type = self.infra.siem_type or "other"
            self.infra.siem_ingest_url = generic

    @staticmethod
    def _looks_secret(url: str) -> bool:
        """Evita persistir URLs con token en query (solo heuristica)."""
        lower = url.lower()
        if re.search(r"token=|apikey=|api_key=|secret=", lower):
            return True
        return False
