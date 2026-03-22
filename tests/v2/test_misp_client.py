"""Tests MISPClient con httpx mockeado (sin red real)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from misp_connector.client import MISPClient


def _client_cm(inner: MagicMock):
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=inner)
    cm.__aexit__ = AsyncMock(return_value=False)
    return cm


@pytest.mark.v2
@pytest.mark.asyncio
async def test_connect_exitoso(misp_env, monkeypatch):
    inner = MagicMock()
    inner.request = AsyncMock(
        return_value=httpx.Response(200, json={"version": "2.4.99"}, request=httpx.Request("GET", "http://x"))
    )
    with patch("misp_connector.client.httpx.AsyncClient", return_value=_client_cm(inner)):
        c = MISPClient()
        assert await c.connect() is True


@pytest.mark.v2
@pytest.mark.asyncio
async def test_connect_api_key_invalida(misp_env, monkeypatch):
    inner = MagicMock()
    inner.request = AsyncMock(
        return_value=httpx.Response(403, json={}, request=httpx.Request("GET", "http://x"))
    )
    with patch("misp_connector.client.httpx.AsyncClient", return_value=_client_cm(inner)):
        c = MISPClient()
        assert await c.connect() is False


@pytest.mark.v2
@pytest.mark.asyncio
async def test_get_attributes_filtra_por_tipo(misp_env):
    # Simula respuesta del servidor ya filtrada por tipo ip-dst
    body = {
        "response": [
            {"Attribute": {"type": "ip-dst", "value": "10.0.0.1"}},
        ]
    }
    inner = MagicMock()
    inner.request = AsyncMock(
        return_value=httpx.Response(200, json=body, request=httpx.Request("POST", "http://x"))
    )
    with patch("misp_connector.client.httpx.AsyncClient", return_value=_client_cm(inner)):
        c = MISPClient()
        attrs = await c.get_attributes(type_filter=["ip-dst"], last="1d", limit=10)
        assert len(attrs) == 1
        assert attrs[0].get("type") == "ip-dst"


@pytest.mark.v2
@pytest.mark.asyncio
async def test_search_attribute_encontrado(misp_env):
    body = {"response": [{"Attribute": {"type": "ip-dst", "value": "1.1.1.1"}}]}
    inner = MagicMock()
    inner.request = AsyncMock(
        return_value=httpx.Response(200, json=body, request=httpx.Request("POST", "http://x"))
    )
    with patch("misp_connector.client.httpx.AsyncClient", return_value=_client_cm(inner)):
        c = MISPClient()
        found = await c.search_attribute("1.1.1.1")
        assert len(found) == 1


@pytest.mark.v2
@pytest.mark.asyncio
async def test_search_attribute_no_encontrado(misp_env):
    inner = MagicMock()
    inner.request = AsyncMock(
        return_value=httpx.Response(404, request=httpx.Request("POST", "http://x"))
    )
    with patch("misp_connector.client.httpx.AsyncClient", return_value=_client_cm(inner)):
        c = MISPClient()
        assert await c.search_attribute("nada") == []


@pytest.mark.v2
@pytest.mark.asyncio
async def test_rate_limit_reintenta(misp_env, monkeypatch):
    monkeypatch.setattr("misp_connector.client.asyncio.sleep", AsyncMock())
    ok = httpx.Response(
        200,
        json={"response": [{"Attribute": {"type": "ip-dst", "value": "9.9.9.9"}}]},
        request=httpx.Request("POST", "http://x"),
    )
    inner = MagicMock()
    inner.request = AsyncMock(side_effect=[httpx.Response(429, request=httpx.Request("POST", "http://x")), ok])
    with patch("misp_connector.client.httpx.AsyncClient", return_value=_client_cm(inner)):
        c = MISPClient()
        attrs = await c.get_attributes(last="1d", limit=5)
        assert len(attrs) == 1


@pytest.mark.v2
@pytest.mark.asyncio
async def test_ssl_error_manejado(misp_env):
    inner = MagicMock()
    inner.request = AsyncMock(side_effect=httpx.RequestError("ssl", request=httpx.Request("GET", "http://x")))
    with patch("misp_connector.client.httpx.AsyncClient", return_value=_client_cm(inner)):
        c = MISPClient()
        status, data = await c._request("GET", "/servers/getPyMISPVersion.json")
        assert status == 0 and data is None
