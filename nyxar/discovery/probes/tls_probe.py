from __future__ import annotations

import logging
import os
from pathlib import Path

from nyxar.discovery.engine import InfrastructureMap

logger = logging.getLogger("nyxar.discovery.probes.tls")


class TlsProbe:
    def __init__(self, infra: InfrastructureMap) -> None:
        self.infra = infra

    async def run(self) -> None:
        try:
            self._detect()
        except Exception as e:
            logger.debug("tls probe: %s", e)

    def _detect(self) -> None:
        for env_key in ("REQUESTS_CA_BUNDLE", "SSL_CERT_FILE", "CURL_CA_BUNDLE"):
            p = (os.environ.get(env_key) or "").strip()
            if p and Path(p).is_file():
                self.infra.ca_internal = True
                self.infra.ca_cert_path = p
                return

        ca_dir = Path("/usr/local/share/ca-certificates")
        if ca_dir.is_dir() and any(ca_dir.iterdir()):
            self.infra.ca_internal = True
            self.infra.ca_cert_path = str(ca_dir)

        if self.infra.proxy_tls_bump:
            self.infra.tls_inspection = True
