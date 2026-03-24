"""Tests D05: TlsAdapter y utilidades del tls_probe."""

from __future__ import annotations

import logging

from nyxar.discovery.adapters.tls_adapter import TlsAdapter, suggest_tls_env
from nyxar.discovery.engine import InfrastructureMap
from nyxar.discovery.probes.tls_probe import _analyze_ca_bundle, _split_pem_certificates


def test_split_pem_empty():
    assert _split_pem_certificates(b"") == []


def test_analyze_empty_bundle(tmp_path):
    p = tmp_path / "empty.crt"
    p.write_bytes(b"")
    assert _analyze_ca_bundle(p) is False


def test_tls_adapter_httpx_verify_true():
    infra = InfrastructureMap()
    ad = TlsAdapter(infra)
    assert ad.get_httpx_client_kwargs() == {"verify": True}


def test_tls_adapter_warns_inspection_without_ca(caplog):
    caplog.set_level(logging.WARNING)
    infra = InfrastructureMap(tls_inspection=True)
    ad = TlsAdapter(infra)
    kw = ad.get_httpx_client_kwargs()
    assert kw == {"verify": True}
    assert "NYXAR_CA_CERT_PATH" in caplog.text


def test_suggest_tls_env():
    infra = InfrastructureMap(ca_cert_path="/etc/ssl/custom/ca.pem")
    env = suggest_tls_env(infra)
    assert env["NYXAR_CA_CERT_PATH"] == "/etc/ssl/custom/ca.pem"
    assert env["SSL_CERT_FILE"] == "/etc/ssl/custom/ca.pem"
