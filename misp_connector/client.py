"""
Cliente async para la API REST de MISP v2.4+.
Documentación: https://www.misp-project.org/openapi/

Autenticación: cabecera Authorization con el valor literal de la API key.
"""

from __future__ import annotations

import asyncio
import os
import time
from typing import Any, Optional

import httpx

from shared.logger import get_logger

logger = get_logger("misp_connector.client")

_MAX_429_RETRIES = 3


def _parse_bool(raw: str | None, default: bool) -> bool:
    if raw is None or raw.strip() == "":
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


def _normalize_base_url(url: str) -> str:
    return url.rstrip("/")


def _safe_json(response: httpx.Response) -> Any | None:
    try:
        return response.json()
    except (ValueError, httpx.DecodingError) as exc:
        logger.warning(
            "Respuesta MISP no es JSON válido",
            extra={"extra": {"status": response.status_code, "detail": str(exc)}},
        )
        return None


def _extract_event_dicts(data: Any) -> list[dict]:
    """Normaliza distintos formatos de respuesta de events/restSearch."""
    out: list[dict] = []
    if isinstance(data, list):
        for item in data:
            if not isinstance(item, dict):
                continue
            ev = item.get("Event")
            if isinstance(ev, dict):
                out.append(ev)
            else:
                out.append(item)
        return out
    if not isinstance(data, dict):
        return out
    resp = data.get("response")
    if isinstance(resp, list):
        for item in resp:
            if not isinstance(item, dict):
                continue
            ev = item.get("Event")
            if isinstance(ev, dict):
                out.append(ev)
            else:
                out.append(item)
        return out
    if isinstance(resp, dict):
        ev = resp.get("Event")
        if isinstance(ev, dict):
            out.append(ev)
        elif isinstance(ev, list):
            out.extend(x for x in ev if isinstance(x, dict))
        if out:
            return out
    ev = data.get("Event")
    if isinstance(ev, dict):
        out.append(ev)
    elif isinstance(ev, list):
        out.extend(x for x in ev if isinstance(x, dict))
    return out


def _extract_attribute_dicts(data: Any) -> list[dict]:
    """Normaliza distintos formatos de respuesta de attributes/restSearch."""
    out: list[dict] = []
    if isinstance(data, list):
        for item in data:
            if not isinstance(item, dict):
                continue
            attr = item.get("Attribute")
            if isinstance(attr, dict):
                out.append(attr)
            else:
                out.append(item)
        return out
    if not isinstance(data, dict):
        return out
    resp = data.get("response")
    if isinstance(resp, list):
        for item in resp:
            if not isinstance(item, dict):
                continue
            attr = item.get("Attribute")
            if isinstance(attr, dict):
                out.append(attr)
            else:
                out.append(item)
        return out
    if isinstance(resp, dict):
        attr = resp.get("Attribute")
        if isinstance(attr, dict):
            out.append(attr)
        elif isinstance(attr, list):
            out.extend(x for x in attr if isinstance(x, dict))
        if out:
            return out
    attr = data.get("Attribute")
    if isinstance(attr, dict):
        out.append(attr)
    elif isinstance(attr, list):
        out.extend(x for x in attr if isinstance(x, dict))
    return out


def _iter_restsearch_items(data: Any) -> list[dict]:
    """Ítems crudos (dict) dentro de response/lista antes de extraer Attribute."""
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]
    if not isinstance(data, dict):
        return []
    resp = data.get("response")
    if isinstance(resp, list):
        return [x for x in resp if isinstance(x, dict)]
    if isinstance(resp, dict):
        inner = resp.get("Attribute")
        if isinstance(inner, list):
            return [{"Attribute": x} for x in inner if isinstance(x, dict)]
        if isinstance(inner, dict):
            return [{"Attribute": inner}]
    attr = data.get("Attribute")
    if isinstance(attr, list):
        return [{"Attribute": x} for x in attr if isinstance(x, dict)]
    if isinstance(attr, dict):
        return [{"Attribute": attr}]
    return []


def _pair_attribute_event(item: dict) -> tuple[dict, dict | None]:
    attr = item.get("Attribute")
    if not isinstance(attr, dict):
        attr = item if item.get("type") is not None and item.get("value") is not None else {}
    ev = item.get("Event")
    if not isinstance(ev, dict):
        ev = None
    return attr, ev


def _extract_attributes_with_event(data: Any) -> list[dict]:
    """Lista de {attribute, event} para ingestor."""
    rows: list[dict] = []
    for item in _iter_restsearch_items(data):
        attr, ev = _pair_attribute_event(item)
        if not attr:
            continue
        rows.append({"attribute": attr, "event": ev})
    return rows


def _event_id_from_create_response(data: Any) -> Optional[str]:
    if not isinstance(data, dict):
        return None
    ev = data.get("Event")
    if isinstance(ev, dict):
        eid = ev.get("id")
        return str(eid) if eid is not None else None
    eid = data.get("id")
    return str(eid) if eid is not None else None


class MISPClient:
    """
    Cliente async para la API REST de MISP v2.4+.
    Documentación: https://www.misp-project.org/openapi/

    Autenticación: header Authorization: {API_KEY}
    Base URL: configurable vía MISP_URL en .env
    """

    def __init__(self) -> None:
        raw_url = os.getenv("MISP_URL", "").strip()
        self._api_key = os.getenv("MISP_API_KEY", "").strip()
        self.base_url = _normalize_base_url(raw_url) if raw_url else ""
        self.verify_ssl = _parse_bool(os.getenv("MISP_VERIFY_SSL"), True)
        self.contribute = _parse_bool(os.getenv("MISP_CONTRIBUTE"), False)
        self.org_name = os.getenv("MISP_ORG_NAME", "CyberPulse-LATAM").strip()

    def _configured(self) -> bool:
        return bool(self.base_url and self._api_key)

    def _headers(self, include_json_content_type: bool) -> dict[str, str]:
        h: dict[str, str] = {
            "Authorization": self._api_key,
            "Accept": "application/json",
        }
        if include_json_content_type:
            h["Content-Type"] = "application/json"
        return h

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json_body: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> tuple[int, Any | None]:
        """
        Ejecuta un request HTTP. Registra latencia en DEBUG.
        403: log CRITICAL, sin reintentos.
        429: backoff exponencial, hasta 3 reintentos.
        """
        if not self._configured():
            logger.error("MISP_URL o MISP_API_KEY no configurados")
            return 0, None

        url = f"{self.base_url}{path}"
        include_ct = method.upper() == "POST" and json_body is not None
        headers = self._headers(include_ct)

        attempt = 0
        last_status = 0
        while attempt <= _MAX_429_RETRIES:
            attempt += 1
            start = time.perf_counter()
            try:
                async with httpx.AsyncClient(timeout=30.0, verify=self.verify_ssl) as client:
                    response = await client.request(
                        method,
                        url,
                        headers=headers,
                        params=params,
                        json=json_body,
                    )
            except httpx.TimeoutException as exc:
                elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
                logger.error(
                    "Timeout llamando a MISP",
                    extra={"extra": {"method": method, "path": path, "ms": elapsed_ms, "detail": str(exc)}},
                )
                return 0, None
            except httpx.RequestError as exc:
                elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
                logger.error(
                    "Error de red llamando a MISP",
                    extra={"extra": {"method": method, "path": path, "ms": elapsed_ms, "detail": str(exc)}},
                )
                return 0, None

            elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
            logger.debug(
                "Llamada API MISP",
                extra={"extra": {"method": method, "path": path, "status": response.status_code, "ms": elapsed_ms}},
            )

            last_status = response.status_code

            if response.status_code == 403:
                logger.critical(
                    "MISP 403: API key inválida o sin permisos",
                    extra={"extra": {"path": path}},
                )
                return response.status_code, _safe_json(response)

            if response.status_code == 429:
                if attempt <= _MAX_429_RETRIES:
                    delay = 2 ** (attempt - 1)
                    logger.warning(
                        "MISP 429 rate limit, reintento",
                        extra={"extra": {"path": path, "attempt": attempt, "sleep_s": delay}},
                    )
                    await asyncio.sleep(delay)
                    continue
                logger.error(
                    "MISP 429: agotados reintentos",
                    extra={"extra": {"path": path}},
                )
                return response.status_code, _safe_json(response)

            data = _safe_json(response)
            return response.status_code, data

        return last_status, None

    async def connect(self) -> bool:
        """
        Verifica conectividad con GET /servers/getPyMISPVersion.json
        Retorna True si la instancia responde y la API key es válida.
        Loguea versión de MISP al conectar.
        """
        status, data = await self._request("GET", "/servers/getPyMISPVersion.json")
        if status == 200 and isinstance(data, dict):
            version = data.get("version") or data.get("Version")
            if version is None:
                pym = data.get("pyMISP")
                if isinstance(pym, dict):
                    version = pym.get("version")
            if version is None:
                version = str(data)[:200]
            logger.info(
                "Conexión MISP OK",
                extra={"extra": {"version": version}},
            )
            return True
        if status == 403:
            return False
        logger.error(
            "No se pudo verificar MISP (getPyMISPVersion)",
            extra={"extra": {"status": status}},
        )
        return False

    async def get_events(
        self,
        last: str = "1d",
        tags: list[str] | None = None,
        threat_level: int | None = None,
        limit: int = 100,
    ) -> list[dict]:
        """
        POST /events/restSearch (restSearch vía JSON).
        Retorna lista de eventos MISP con sus atributos (IOCs) cuando la API los incluye.
        """
        body: dict[str, Any] = {
            "returnFormat": "json",
            "publish_timestamp": last,
            "limit": limit,
        }
        if tags:
            body["tags"] = tags
        if threat_level is not None:
            body["threat_level_id"] = threat_level

        status, data = await self._request("POST", "/events/restSearch", json_body=body)
        if status == 404:
            return []
        if status != 200 or data is None:
            return []
        return _extract_event_dicts(data)

    async def get_attributes(
        self,
        event_id: str | None = None,
        type_filter: list[str] | None = None,
        last: str = "1d",
        limit: int = 1000,
        publish_timestamp: str | int | list[Any] | None = None,
        include_event_context: bool = False,
    ) -> list[dict]:
        """
        POST /attributes/restSearch
        Retorna IOCs individuales directamente, o con contexto del evento si
        include_event_context=True (lista de dicts con keys attribute y event).

        publish_timestamp: si se informa (unix int, shorthand tipo 7d, o rango
        aceptado por MISP), sustituye a last en el cuerpo JSON.
        """
        ts = publish_timestamp if publish_timestamp is not None else last
        body: dict[str, Any] = {
            "returnFormat": "json",
            "publish_timestamp": ts,
            "limit": limit,
        }
        if event_id:
            body["eventid"] = event_id
        if type_filter:
            body["type"] = type_filter

        status, data = await self._request("POST", "/attributes/restSearch", json_body=body)
        if status == 404:
            return []
        if status != 200 or data is None:
            return []
        if include_event_context:
            return _extract_attributes_with_event(data)
        return _extract_attribute_dicts(data)

    async def create_event(self, event_data: dict) -> Optional[str]:
        """
        POST /events/add
        Crea un nuevo evento MISP con IOCs propios.
        Retorna el event_id generado por MISP.
        Solo si MISP_CONTRIBUTE=true en .env (opt-in explícito).
        """
        if not self.contribute:
            logger.debug("create_event omitido: MISP_CONTRIBUTE=false")
            return None

        payload = dict(event_data)
        if "info" not in payload and self.org_name:
            payload["info"] = f"{self.org_name} — evento CyberPulse"

        status, data = await self._request("POST", "/events/add", json_body=payload)
        if status == 404:
            return None
        if status != 200 or data is None:
            return None
        return _event_id_from_create_response(data)

    async def add_attribute(self, event_id: str, attribute: dict) -> bool:
        """
        POST /attributes/add/{event_id}
        Agrega un IOC a un evento existente.
        """
        if not self.contribute:
            logger.debug("add_attribute omitido: MISP_CONTRIBUTE=false")
            return False

        path = f"/attributes/add/{event_id}"
        status, data = await self._request("POST", path, json_body=attribute)
        if status == 404:
            return False
        if status != 200:
            return False
        if isinstance(data, dict):
            if data.get("errors"):
                logger.error(
                    "MISP rechazó el atributo",
                    extra={"extra": {"errors": data.get("errors")}},
                )
                return False
            saved = data.get("Attribute") or data.get("attribute")
            if isinstance(saved, dict) and saved.get("id"):
                return True
            if data.get("saved", False) is True:
                return True
        return True

    async def search_attribute(self, valor: str) -> list[dict]:
        """
        Busca un valor específico (IP, dominio, hash) en atributos vía restSearch.
        POST /attributes/restSearch con value.
        """
        body: dict[str, Any] = {
            "returnFormat": "json",
            "value": valor,
            "limit": 1000,
        }
        status, data = await self._request("POST", "/attributes/restSearch", json_body=body)
        if status == 404:
            return []
        if status != 200 or data is None:
            return []
        return _extract_attribute_dicts(data)
