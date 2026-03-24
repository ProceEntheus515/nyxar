"""
Coexistencia SIEM (D06): consumo desde API (modo A) y publicacion hacia SIEM (modo B).
Modo C sin SIEM: no usar esta clase. Tokens solo en runtime (siem_config), no en InfrastructureMap.
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Any, Optional

from nyxar.discovery.adapters.tls_adapter import TlsAdapter
from nyxar.discovery.engine import InfrastructureMap

logger = logging.getLogger("nyxar.discovery.adapters.siem")


class SiemAdapter:
    """
    Cliente analitico hacia Splunk/Elastic (consume) y fuente hacia HEC/indices (publish).
    """

    def __init__(
        self,
        infra: InfrastructureMap,
        tls_adapter: Optional[TlsAdapter] = None,
    ) -> None:
        self.infra = infra
        self._tls = tls_adapter if tls_adapter is not None else TlsAdapter(infra)

    def _verify(self) -> bool | str:
        return self._tls.get_httpx_client_kwargs().get("verify", True)

    async def consume_from_splunk(
        self,
        splunk_url: str,
        token: str,
        search_query: str = "search index=* earliest=-1m",
    ) -> list[dict[str, Any]]:
        """Crea job de busqueda Splunk y devuelve resultados (REST mgmt, no HEC)."""
        try:
            import httpx
        except ImportError as e:
            raise RuntimeError("httpx es requerido para consume_from_splunk") from e

        base = splunk_url.rstrip("/")
        verify = self._verify()
        headers = {"Authorization": f"Splunk {token}"}

        async with httpx.AsyncClient(verify=verify, timeout=60.0) as client:
            r = await client.post(
                f"{base}/services/search/jobs",
                headers=headers,
                data={
                    "search": search_query,
                    "output_mode": "json",
                    "earliest_time": "-1m",
                    "latest_time": "now",
                },
            )
            r.raise_for_status()
            body = r.json()
            sid = body.get("sid")
            if not sid:
                logger.warning("Splunk: respuesta sin sid")
                return []

            for _ in range(40):
                await asyncio.sleep(0.5)
                st = await client.get(
                    f"{base}/services/search/jobs/{sid}",
                    headers=headers,
                    params={"output_mode": "json"},
                )
                st.raise_for_status()
                entry = (st.json().get("entry") or [{}])[0]
                content = entry.get("content") or {}
                if content.get("isDone") in (True, "1", 1):
                    break
            else:
                logger.warning("Splunk: job %s no termino a tiempo", sid)
                return []

            results_r = await client.get(
                f"{base}/services/search/jobs/{sid}/results",
                headers=headers,
                params={"output_mode": "json", "count": 1000},
            )
            results_r.raise_for_status()
            return results_r.json().get("results", [])

    async def consume_from_elastic(
        self,
        elastic_url: str,
        api_key: str,
        index_pattern: str = "logs-*",
        size: int = 1000,
    ) -> list[dict[str, Any]]:
        """Busqueda reciente en Elasticsearch (API key id:key en base64)."""
        try:
            import httpx
        except ImportError as e:
            raise RuntimeError("httpx es requerido para consume_from_elastic") from e

        base = elastic_url.rstrip("/")
        verify = self._verify()
        query = {
            "query": {
                "range": {
                    "@timestamp": {
                        "gte": "now-1m",
                        "lt": "now",
                    }
                }
            },
            "size": size,
            "sort": [{"@timestamp": {"order": "desc"}}],
        }
        path = f"{base}/{index_pattern}/_search"
        headers = {
            "Authorization": f"ApiKey {api_key}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(verify=verify, timeout=60.0) as client:
            r = await client.post(path, headers=headers, json=query)
            r.raise_for_status()
            hits = r.json().get("hits", {}).get("hits", [])
            return [h.get("_source") or {} for h in hits if isinstance(h, dict)]

    async def publish_to_siem(
        self,
        incident: dict[str, Any],
        siem_type: str,
        siem_config: dict[str, Any],
    ) -> bool:
        """
        Publica incidente NYXAR al SIEM. siem_config debe incluir url y credenciales de uso unico.
        splunk: hec_token; elastic: api_key, opcional index (default nyxar-incidents).
        """
        try:
            import httpx
        except ImportError:
            return False

        st = (siem_type or "").strip().lower()
        verify = self._verify()
        version = os.environ.get("NYXAR_VERSION", "1.0.0")

        if st == "splunk":
            url = (siem_config.get("url") or "").rstrip("/")
            hec = siem_config.get("hec_token") or siem_config.get("token")
            if not url or not hec:
                return False
            payload = {
                "time": datetime.now(timezone.utc).timestamp(),
                "source": "nyxar",
                "sourcetype": "nyxar:incident",
                "event": {**incident, "_nyxar_version": version},
            }
            async with httpx.AsyncClient(verify=verify, timeout=30.0) as client:
                r = await client.post(
                    f"{url}/services/collector/event",
                    headers={"Authorization": f"Splunk {hec}"},
                    json=payload,
                )
                return r.status_code == 200

        if st == "elastic":
            url = (siem_config.get("url") or "").rstrip("/")
            api_key = siem_config.get("api_key")
            index = (siem_config.get("index") or "nyxar-incidents").strip("/")
            if not url or not api_key:
                return False
            doc = {
                "@timestamp": datetime.now(timezone.utc).isoformat(),
                **incident,
            }
            async with httpx.AsyncClient(verify=verify, timeout=30.0) as client:
                r = await client.post(
                    f"{url}/{index}/_doc",
                    headers={
                        "Authorization": f"ApiKey {api_key}",
                        "Content-Type": "application/json",
                    },
                    json=doc,
                )
                return r.status_code in (200, 201)

        logger.debug("publish_to_siem: tipo SIEM no soportado: %s", siem_type)
        return False


def suggest_siem_env(infra: InfrastructureMap) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if infra.siem_ingest_url:
        if infra.siem_type == "splunk":
            out["SPLUNK_HEC_URL"] = infra.siem_ingest_url
        elif infra.siem_type == "elastic":
            out["ELASTICSEARCH_URL"] = infra.siem_ingest_url
        else:
            out["NYXAR_SIEM_INGEST_URL"] = infra.siem_ingest_url
    if infra.siem_api_url:
        out["NYXAR_SIEM_API_URL"] = infra.siem_api_url
        if infra.siem_type == "splunk":
            out["SPLUNK_MGMT_URL"] = infra.siem_api_url
        elif infra.siem_type == "elastic" and "ELASTICSEARCH_URL" not in out:
            out["ELASTICSEARCH_URL"] = infra.siem_api_url
    return out
