"""Tests del adaptador de logs de proxy (D02)."""

from __future__ import annotations

from nyxar.discovery.adapters.proxy_adapter import ProxyAdapter, suggest_proxy_env
from nyxar.discovery.engine import InfrastructureMap


def test_parse_squid_native():
    infra = InfrastructureMap(proxy_present=True, proxy_log_format="squid_native")
    ad = ProxyAdapter(infra)
    line = "1742400000.000  42 192.168.1.45 TCP_MISS/200 8523 GET http://example.com/"
    row = ad.parse_line(line)
    assert row is not None
    assert row["client"] == "192.168.1.45"
    assert row["method"] == "GET"
    assert row["status_code"] == 200
    assert row["url"] == "http://example.com/"


def test_parse_combined_log_format():
    infra = InfrastructureMap(proxy_present=True, proxy_log_format="combined_log_format")
    ad = ProxyAdapter(infra)
    line = (
        '192.168.1.45 - - [20/Mar/2026:10:00:00 +0000] '
        '"GET /path HTTP/1.1" 200 1234'
    )
    row = ad.parse_line(line)
    assert row is not None
    assert row["client"] == "192.168.1.45"
    assert row["method"] == "GET"
    assert row["url"] == "/path"
    assert row["status_code"] == 200
    assert row["bytes"] == 1234


def test_parse_json_log():
    infra = InfrastructureMap(proxy_present=True, proxy_log_format="json")
    ad = ProxyAdapter(infra)
    line = '{"timestamp": 1, "clientip": "10.0.0.1", "url": "https://x.test/", "method": "GET", "status": 204}'
    row = ad.parse_line(line)
    assert row is not None
    assert row["client"] == "10.0.0.1"
    assert row["status_code"] == 204


def test_parse_best_effort():
    infra = InfrastructureMap(proxy_present=True, proxy_log_format="unknown")
    ad = ProxyAdapter(infra)
    row = ad.parse_line("noise 203.0.113.7 noise https://ex.com/a")
    assert row is not None
    assert row["client"] == "203.0.113.7"
    assert row["url"] == "https://ex.com/a"


def test_parse_line_absent_proxy():
    infra = InfrastructureMap(proxy_present=False, proxy_log_path=None)
    ad = ProxyAdapter(infra)
    assert ad.parse_line("anything") is None


def test_suggest_proxy_env():
    infra = InfrastructureMap(
        proxy_present=True,
        proxy_host="proxy.corp",
        proxy_port=3128,
        proxy_log_path="/var/log/squid/access.log",
        proxy_log_format="squid_native",
        proxy_type="zscaler",
    )
    env = suggest_proxy_env(infra)
    assert "HTTP_PROXY" in env
    assert "proxy.corp:3128" in env["HTTP_PROXY"]
    assert env.get("NYXAR_PROXY_LOG_PATH") == "/var/log/squid/access.log"
