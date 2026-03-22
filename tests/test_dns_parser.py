import pytest
from collector.parsers.dns_parser import DnsParser

@pytest.fixture
def parser(mocker=None):
    """DnsParser sin RedisBus real — pasamos un mock básico."""
    from unittest.mock import AsyncMock
    mock_redis = AsyncMock()
    return DnsParser(log_path="/dev/null", redis_bus=mock_redis)

def test_parse_line_query_a(parser):
    line = "Oct 19 14:15:22 dnsmasq[1234]: query[A] example.com from 192.168.1.50"
    res = parser._parse_line(line)
    assert res is not None
    assert res['domain'] == 'example.com'
    assert res['client'] == '192.168.1.50'
    assert res['type'] == 'A'

def test_parse_line_query_aaaa(parser):
    line = "Oct 19 14:15:22 dnsmasq[1234]: query[AAAA] ipv6.example.com from 192.168.1.50"
    res = parser._parse_line(line)
    assert res is not None
    assert res['type'] == 'AAAA'
    assert res['domain'] == 'ipv6.example.com'

def test_parse_line_blocked(parser):
    line = "Oct 19 14:15:22 dnsmasq[1234]: gravity blocked evil.com for 192.168.1.50"
    res = parser._parse_line(line)
    assert res is not None
    assert res['blocked'] is True
    assert res['domain'] == 'evil.com'
    assert res['status'] == 'BLOCKED'

def test_parse_line_reply(parser):
    line = "Oct 19 14:15:22 dnsmasq[1234]: reply example.com is 93.184.216.34"
    assert parser._parse_line(line) is None

def test_parse_line_cached(parser):
    line = "Oct 19 14:15:22 dnsmasq[1234]: cached example.com is 93.184.216.34"
    assert parser._parse_line(line) is None

def test_parse_line_dominio_arpa(parser):
    line = "Oct 19 14:15:22 dnsmasq[1234]: query[PTR] 50.1.168.192.in-addr.arpa from 192.168.1.1"
    res = parser._parse_line(line)
    if res:
        assert parser._is_internal_domain(res['domain']) is True

def test_parse_line_formato_invalido(parser):
    line = "Linea random sin sentido lol"
    assert parser._parse_line(line) is None

def test_is_internal_domain_local(parser):
    assert parser._is_internal_domain("server.empresa.local") is True
    assert parser._is_internal_domain("host.lan") is False  # .lan no está explícita, depende config

def test_is_internal_domain_arpa(parser):
    assert parser._is_internal_domain("47.101.220.185.in-addr.arpa") is True

def test_is_internal_domain_externo(parser):
    assert parser._is_internal_domain("google.com") is False
    assert parser._is_internal_domain("malicious.xyz") is False
