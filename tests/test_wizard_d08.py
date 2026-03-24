"""Tests D08: wizard_env y guardado fragmento .env."""

from __future__ import annotations

from pathlib import Path

from nyxar.discovery.engine import InfrastructureMap
from nyxar.discovery.wizard import _save_to_env
from nyxar.discovery.wizard_env import format_env_block, merge_suggested_env


def test_merge_suggested_env_includes_network_and_method():
    infra = InfrastructureMap(
        network_range="10.0.0.0/24",
        dns_server="10.0.0.2",
        dns_type="bind9",
    )
    m = merge_suggested_env(infra)
    assert m["NETWORK_RANGE"] == "10.0.0.0/24"
    assert m["NYXAR_DISCOVERY_METHOD"] == "assisted"
    assert m["NYXAR_DNS_SERVER"] == "10.0.0.2"


def test_format_env_block_has_header():
    text = format_env_block({"A": "1"})
    assert "NYXAR Setup Wizard" in text
    assert "A=1" in text


def test_save_to_env_creates_file(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    _save_to_env("X=1\n", ["SECRET=z"], env_file)
    content = env_file.read_text(encoding="utf-8")
    assert "X=1" in content
    assert "SECRET=z" in content


def test_firewall_adapter_cisco_branch():
    from nyxar.discovery.adapters.firewall_adapter import generate_firewall_config_instructions

    t = generate_firewall_config_instructions("192.168.1.10", "cisco")
    assert "192.168.1.10" in t
    assert "Cisco" in t or "cisco" in t.lower()
