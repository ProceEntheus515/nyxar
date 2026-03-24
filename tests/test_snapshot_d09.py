"""Tests D09: snapshots y reporte redactado."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from nyxar.discovery.engine import InfrastructureMap
from nyxar.discovery.snapshot import ConfigSnapshot


def test_compare_snapshots_diff():
    a = InfrastructureMap(dns_server="10.0.0.1", proxy_present=False)
    b = InfrastructureMap(dns_server="10.0.0.2", proxy_present=False)
    diff = ConfigSnapshot.compare_snapshots(a, b)
    assert "dns_server" in diff
    assert diff["dns_server"]["antes"] == "10.0.0.1"


def test_save_snapshot_writes_file(tmp_path: Path) -> None:
    infra = InfrastructureMap(dns_server="10.0.0.53", discovered_at="2025-01-01T00:00:00Z")
    snap = ConfigSnapshot(snapshot_dir=tmp_path / "snaps")
    sid = snap.save_snapshot(infra)
    files = list((tmp_path / "snaps").glob("map_*.json"))
    assert len(files) == 1
    assert sid in files[0].name
    data = json.loads(files[0].read_text(encoding="utf-8"))
    assert data["dns_server"] == "10.0.0.53"


def test_redacted_report_no_raw_dns_ip():
    infra = InfrastructureMap(
        dns_server="10.99.99.99",
        dns_type="bind9",
        discovered_at="x",
        confidence=0.5,
    )
    text = ConfigSnapshot.generate_redacted_report(infra)
    assert "10.99.99.99" not in text
    parsed = json.loads(text)
    assert parsed["infrastructure"]["has_dns"] is True
    assert parsed["infrastructure"]["dns_type"] == "bind9"


def test_load_roundtrip(tmp_path: Path) -> None:
    p = tmp_path / "m.json"
    infra = InfrastructureMap(network_range="192.168.0.0/24")
    p.write_text(json.dumps(asdict(infra), default=str), encoding="utf-8")
    snap = ConfigSnapshot()
    loaded = snap.load_map_file(p)
    assert loaded.network_range == "192.168.0.0/24"
