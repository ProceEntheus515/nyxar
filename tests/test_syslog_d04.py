"""Tests D04: detector syslog, parsers y conversion a Evento."""

from __future__ import annotations

import asyncio

from nyxar.discovery.adapters.firewall_adapter import generate_firewall_config_instructions
from nyxar.discovery.syslog.detector import SyslogFormatDetector
from nyxar.discovery.syslog.parsers import (
    CefParser,
    FortinetParser,
    JsonFirewallParser,
    Rfc3164Parser,
)


def test_detector_cef():
    d = SyslogFormatDetector()
    assert d.detect("CEF:0|Vendor|Prod|1.0|10|test|5|src=1.1.1.1") == "cef"


def test_detector_leef():
    d = SyslogFormatDetector()
    assert d.detect("LEEF:1.0|IBM|QRadar|1.0|123|cat=foo") == "leef"


def test_detector_json():
    d = SyslogFormatDetector()
    assert d.detect('{"src":"1.1.1.1","dst":"2.2.2.2"}') == "json"


def test_detector_fortinet():
    d = SyslogFormatDetector()
    raw = 'date=2026-03-20 time=12:00:00 devname="FW" type=traffic'
    assert d.detect(raw) == "fortinet"


def test_detector_rfc5424():
    d = SyslogFormatDetector()
    assert d.detect("<34>1 2026-03-20T12:00:00Z host app proc - msg") == "rfc5424"


def test_cef_parser():
    p = CefParser()
    raw = "prefix CEF:0|TestCo|FW|1|1|Deny|10|src=10.0.0.5 dst=203.0.113.1 act=block"
    o = p.parse(raw, "192.168.1.1")
    assert o is not None
    assert o["src_ip"] == "10.0.0.5"
    assert o["dst_ip"] == "203.0.113.1"


def test_fortinet_parser():
    p = FortinetParser()
    raw = (
        'date=2026-03-20 time=14:32:11 devname="FW01" '
        'srcip=10.1.1.1 dstip=203.0.113.7 action=deny proto=6'
    )
    o = p.parse(raw, "10.0.0.1")
    assert o is not None
    assert o["src_ip"] == "10.1.1.1"
    assert o["dst_ip"] == "203.0.113.7"
    assert o["action"] == "DENY"


def test_json_parser():
    p = JsonFirewallParser()
    o = p.parse('<0>1 host: {"src_ip":"10.0.0.2","dst_ip":"198.51.100.1"}', "10.0.0.1")
    assert o is not None
    assert o["src_ip"] == "10.0.0.2"


def test_rfc3164_parser():
    p = Rfc3164Parser()
    o = p.parse("<30>Mar 20 12:00:00 fw1 kernel: drop", "192.168.0.1")
    assert o is not None
    assert o["src_ip"] == "192.168.0.1"


def test_generate_firewall_instructions():
    t = generate_firewall_config_instructions("10.20.30.40", "fortinet")
    assert "10.20.30.40" in t
    assert "514" in t


def test_process_message_publishes_event():
    from nyxar.discovery.engine import InfrastructureMap
    from nyxar.discovery.syslog.receiver import SyslogReceiver

    published: list[dict] = []

    class FakeBus:
        STREAM_RAW = "events:raw"

        async def publish_event(self, stream: str, evento: dict) -> str:
            published.append({"stream": stream, "evento": evento})
            return "1-0"

    infra = InfrastructureMap()
    recv = SyslogReceiver(FakeBus(), infra)
    recv._detected_format = "rfc3164"
    asyncio.run(recv._process_message("<30>test: traffic", "10.0.0.1"))
    assert published
    assert published[0]["evento"]["source"] == "firewall"
