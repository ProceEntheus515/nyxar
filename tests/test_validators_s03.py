"""Tests del módulo api.validators (PROMPTS_V6 S03)."""

from __future__ import annotations

import pytest

from api.validators import (
    normalize_domain_strip_port,
    validate_domain,
    validate_event_id_param,
    validate_ip,
    validate_mongodb_query,
    validate_no_path_traversal,
    sanitize_for_prompt,
)


def test_validate_ip_ok():
    assert validate_ip("192.168.0.1") == "192.168.0.1"
    assert validate_ip(" 2001:db8::1 ") == "2001:db8::1"


def test_validate_ip_rejects():
    with pytest.raises(ValueError):
        validate_ip("not-an-ip")


def test_validate_domain_ok():
    assert validate_domain("evil.com") == "evil.com"
    assert validate_domain("Sub.EXAMPLE.co.uk") == "sub.example.co.uk"


def test_validate_domain_rejects_port_and_traversal():
    with pytest.raises(ValueError):
        validate_domain("x.com:443")
    with pytest.raises(ValueError):
        validate_domain("../etc")


def test_normalize_domain_strip_port():
    assert normalize_domain_strip_port("malicious.com:443") == "malicious.com"


def test_validate_no_path_traversal():
    with pytest.raises(ValueError):
        validate_no_path_traversal("a../b")


def test_sanitize_for_prompt_strips_control():
    out = sanitize_for_prompt("a\x00b\nc", max_length=10)
    assert "\x00" not in out
    assert "\n" in out


def test_validate_mongodb_query_rejects_where():
    with pytest.raises(ValueError, match="prohibido"):
        validate_mongodb_query({"$where": "1"})


def test_validate_mongodb_query_nested():
    with pytest.raises(ValueError):
        validate_mongodb_query({"a": {"b": {"$expr": True}}})


def test_validate_event_id_param():
    assert validate_event_id_param("evt_1730000000_abcd") == "evt_1730000000_abcd"
    assert validate_event_id_param("evt_test_1730000000_a1b2") == "evt_test_1730000000_a1b2"


def test_validate_event_id_param_rejects():
    with pytest.raises(ValueError):
        validate_event_id_param("../../../x")
