"""Tests D06: SiemAdapter publish y suggest_siem_env."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from nyxar.discovery.adapters.siem_adapter import SiemAdapter, suggest_siem_env
from nyxar.discovery.engine import InfrastructureMap


def test_suggest_siem_env_api_and_ingest():
    infra = InfrastructureMap(
        siem_present=True,
        siem_type="splunk",
        siem_ingest_url="https://splunk:8088/services/collector/event",
        siem_api_url="https://splunk:8089",
    )
    env = suggest_siem_env(infra)
    assert "SPLUNK_HEC_URL" in env
    assert env["SPLUNK_MGMT_URL"] == "https://splunk:8089"
    assert env["NYXAR_SIEM_API_URL"] == "https://splunk:8089"


def test_publish_splunk_hec_uses_json():
    async def _run() -> None:
        infra = InfrastructureMap()
        ad = SiemAdapter(infra)
        resp = MagicMock()
        resp.status_code = 200
        client_instance = MagicMock()
        client_instance.post = AsyncMock(return_value=resp)
        client_instance.__aenter__ = AsyncMock(return_value=client_instance)
        client_instance.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient") as ac:
            ac.return_value = client_instance
            ok = await ad.publish_to_siem(
                {"title": "x"},
                "splunk",
                {"url": "https://hec:8088", "hec_token": "abc"},
            )
            assert ok
            client_instance.post.assert_awaited()
            call_kw = client_instance.post.call_args
            assert call_kw is not None
            assert "json" in call_kw.kwargs

    asyncio.run(_run())


def test_publish_elastic():
    async def _run() -> None:
        infra = InfrastructureMap()
        ad = SiemAdapter(infra)
        resp = MagicMock()
        resp.status_code = 201
        client_instance = MagicMock()
        client_instance.post = AsyncMock(return_value=resp)
        client_instance.__aenter__ = AsyncMock(return_value=client_instance)
        client_instance.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient") as ac:
            ac.return_value = client_instance
            ok = await ad.publish_to_siem(
                {"title": "y"},
                "elastic",
                {
                    "url": "https://es:9200",
                    "api_key": "k",
                    "index": "nyxar-incidents",
                },
            )
            assert ok

    asyncio.run(_run())


def test_publish_unsupported():
    async def _run() -> None:
        infra = InfrastructureMap()
        ad = SiemAdapter(infra)
        ok = await ad.publish_to_siem({}, "unknown", {})
        assert not ok

    asyncio.run(_run())
