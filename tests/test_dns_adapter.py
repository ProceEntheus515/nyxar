"""Tests del adaptador DNS (D03)."""

from __future__ import annotations

from nyxar.discovery.adapters.dns_adapter import DnsAdapter, suggest_dns_env
from nyxar.discovery.engine import InfrastructureMap


def test_parse_pihole_dnsmasq_line():
    infra = InfrastructureMap(dns_log_format="pihole")
    ad = DnsAdapter(infra)
    line = "Mar 20 10:00:00 dnsmasq[123]: query[A] google.com from 192.168.0.5"
    row = ad.parse_line(line)
    assert row is not None
    assert row["domain"] == "google.com"
    assert row["client"] == "192.168.0.5"
    assert row["query_type"] == "A"


def test_parse_bind_query():
    infra = InfrastructureMap(dns_log_format="bind_query")
    ad = DnsAdapter(infra)
    line = "client 192.0.2.10#54321: query: example.org IN A +E(0)K (192.0.2.10)"
    row = ad.parse_line(line)
    assert row is not None
    assert row["client"] == "192.0.2.10"
    assert row["domain"] == "example.org"
    assert row["query_type"] == "A"


def test_parse_unbound():
    infra = InfrastructureMap(dns_log_format="unbound")
    ad = DnsAdapter(infra)
    line = "unbound: info: query: example.com IN A +E(0) from 10.0.0.2"
    row = ad.parse_line(line)
    assert row is not None
    assert row["domain"] == "example.com"
    assert row["query_type"] == "A"
    assert row["client"] == "10.0.0.2"


def test_parse_pihole_api_json():
    infra = InfrastructureMap(dns_log_format="pihole_api")
    ad = DnsAdapter(infra)
    line = '{"dns_queries_today": 100, "domains_being_blocked": 5}'
    row = ad.parse_line(line)
    assert row is not None
    assert row["dns_queries_today"] == 100


def test_suggest_dns_env():
    infra = InfrastructureMap(
        dns_log_path="/var/log/pihole.log",
        dns_api_url="http://pi.hole/admin/api.php",
        dns_type="pihole",
        dns_server="10.0.0.1",
    )
    env = suggest_dns_env(infra)
    assert env["NYXAR_DNS_LOG_PATH"] == "/var/log/pihole.log"
    assert "PIHOLE_API_URL" in env
    assert env["NYXAR_DNS_SERVER"] == "10.0.0.1"
