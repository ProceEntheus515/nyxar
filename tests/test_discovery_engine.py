"""Tests del motor de discovery NYXAR (mapa, confianza, persistencia)."""

from __future__ import annotations

import tempfile
from pathlib import Path

from nyxar.discovery.engine import (
    DiscoveryEngine,
    InfrastructureMap,
    _infra_from_json,
)


def test_calculate_confidence_bounds():
    eng = DiscoveryEngine()
    empty = InfrastructureMap()
    c0 = eng._calculate_confidence(empty)
    assert 0.0 <= c0 <= 1.0

    full = InfrastructureMap(
        dns_server="10.0.0.1",
        dns_log_path="/var/log/pihole.log",
        proxy_present=True,
        proxy_log_path="/var/log/squid/access.log",
        syslog_port=514,
        wazuh_present=True,
    )
    c1 = eng._calculate_confidence(full)
    assert c1 > c0


def test_save_and_load_roundtrip():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "map.json"
        eng = DiscoveryEngine()
        eng.MAP_PATH = path
        infra = InfrastructureMap(
            network_range="192.168.1.0/24",
            dns_server="192.168.1.1",
            discovery_method="auto",
        )
        eng._save_map(infra)
        loaded = eng.load_existing_map()
        assert loaded is not None
        assert loaded.network_range == "192.168.1.0/24"
        assert loaded.dns_server == "192.168.1.1"


def test_infra_from_json_ignores_unknown_keys():
    raw = {
        "network_range": "10.0.0.0/8",
        "future_field_xyz": "ignore",
        "vlans_detected": ["10", "20"],
    }
    m = _infra_from_json(raw)
    assert m.network_range == "10.0.0.0/8"
    assert m.vlans_detected == ["10", "20"]
    assert not hasattr(m, "future_field_xyz")
