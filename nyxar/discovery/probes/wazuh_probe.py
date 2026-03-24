from __future__ import annotations

import asyncio
import logging
import os
from urllib.parse import urlparse

from nyxar.discovery.engine import InfrastructureMap

logger = logging.getLogger("nyxar.discovery.probes.wazuh")


class WazuhProbe:
    def __init__(self, infra: InfrastructureMap) -> None:
        self.infra = infra

    async def run(self) -> None:
        try:
            await self._detect()
        except Exception as e:
            logger.debug("wazuh probe: %s", e)

    async def _detect(self) -> None:
        explicit = (os.environ.get("WAZUH_API_URL") or "").strip()
        if explicit:
            self.infra.wazuh_present = True
            self.infra.wazuh_api_url = explicit.rstrip("/")
            self.infra.wazuh_api_version = (
                os.environ.get("WAZUH_API_VERSION") or "v4"
            ).strip()
            return

        host = (os.environ.get("WAZUH_MANAGER_HOST") or "wazuh-manager").strip()
        port = int((os.environ.get("WAZUH_API_PORT") or "55000").strip() or "55000")
        timeout = float(os.environ.get("NYXAR_PROBE_TIMEOUT_S", "2") or "2")

        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port),
                timeout=timeout,
            )
            writer.close()
            await writer.wait_closed()
            self.infra.wazuh_present = True
            scheme = (os.environ.get("WAZUH_API_SCHEME") or "https").strip()
            self.infra.wazuh_api_url = f"{scheme}://{host}:{port}"
            self.infra.wazuh_api_version = "v4"
        except Exception:
            pass

        wh = (os.environ.get("WAZUH_WEBHOOK_URL") or "").strip()
        if wh:
            self.infra.wazuh_webhook_available = True
            if urlparse(wh).scheme:
                self.infra.wazuh_present = True
