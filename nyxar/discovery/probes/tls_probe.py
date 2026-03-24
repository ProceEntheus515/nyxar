"""
Sondeo TLS (D05): CA interna en bundles y directorios; inspeccion TLS via proxy (CONNECT).
Sin desactivar verificacion SSL global.
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
import socket
import ssl
from pathlib import Path

from nyxar.discovery.engine import InfrastructureMap

logger = logging.getLogger("nyxar.discovery.probes.tls")

CA_BUNDLE_PATHS = (
    "/etc/ssl/certs/ca-certificates.crt",
    "/etc/pki/tls/certs/ca-bundle.crt",
    "/etc/ssl/ca-bundle.pem",
)

PUBLIC_CA_ORGS = frozenset(
    {
        "DigiCert",
        "Comodo",
        "GlobalSign",
        "VeriSign",
        "Symantec",
        "GeoTrust",
        "Thawte",
        "RapidSSL",
        "Let's Encrypt",
        "IdenTrust",
        "ISRG",
        "Sectigo",
        "Google Trust Services",
        "Google Trust Services LLC",
        "Microsoft Corporation",
        "Amazon",
        "DigiCert Inc",
        "DigiCert, Inc.",
    }
)

KNOWN_ISSUER_SUBSTR = (
    "Google Trust",
    "DigiCert",
    "Let's Encrypt",
    "GlobalSign",
    "Comodo",
    "Sectigo",
    "Amazon",
    "Microsoft",
    "Entrust",
    "Go Daddy",
    "Starfield",
    "Apple",
    "Buypass",
)


class TlsProbe:
    def __init__(self, infra: InfrastructureMap) -> None:
        self.infra = infra

    async def run(self) -> None:
        try:
            await asyncio.gather(
                self._detect_internal_ca(),
                self._detect_tls_inspection(),
            )
        except Exception as e:
            logger.debug("tls probe: %s", e)

    async def _detect_internal_ca(self) -> None:
        await asyncio.to_thread(self._detect_internal_ca_sync)

    def _detect_internal_ca_sync(self) -> None:
        manual = (os.environ.get("NYXAR_CA_CERT_PATH") or "").strip()
        if manual and Path(manual).exists():
            self.infra.ca_internal = True
            self.infra.ca_cert_path = str(Path(manual).resolve())
            return

        for env_key in ("REQUESTS_CA_BUNDLE", "SSL_CERT_FILE", "CURL_CA_BUNDLE"):
            p = (os.environ.get(env_key) or "").strip()
            if p and Path(p).is_file():
                self.infra.ca_internal = True
                self.infra.ca_cert_path = str(Path(p).resolve())
                return

        local = Path("/usr/local/share/ca-certificates")
        if local.is_dir():
            crts = sorted(local.glob("*.crt"))
            if crts:
                self.infra.ca_internal = True
                self.infra.ca_cert_path = str(crts[0].resolve())
                return

        for ca_path in CA_BUNDLE_PATHS:
            p = Path(ca_path)
            if p.is_file() and _analyze_ca_bundle(p):
                self.infra.ca_internal = True
                self.infra.ca_cert_path = str(p.resolve())
                return

    async def _detect_tls_inspection(self) -> None:
        if not self.infra.proxy_present:
            return
        host = self.infra.proxy_host
        port = self.infra.proxy_port
        if not host or not port:
            return
        try:
            bump, org = await asyncio.to_thread(
                _sync_probe_tls_inspection, host, int(port)
            )
            if bump:
                self.infra.tls_inspection = True
                self.infra.proxy_tls_bump = True
                logger.info(
                    "Inspeccion TLS detectada en proxy; emisor aparente: %s",
                    org or "(sin organizationName)",
                )
        except Exception as e:
            logger.debug("tls inspection probe: %s", e)

        if self.infra.proxy_tls_bump:
            self.infra.tls_inspection = True


def _split_pem_certificates(data: bytes) -> list[bytes]:
    pattern = re.compile(
        rb"-----BEGIN CERTIFICATE-----.*?-----END CERTIFICATE-----",
        re.DOTALL,
    )
    return list(pattern.findall(data))


def _analyze_ca_bundle(bundle_path: Path) -> bool:
    try:
        data = bundle_path.read_bytes()
    except OSError:
        return False
    blocks = _split_pem_certificates(data)
    if not blocks:
        return False

    try:
        from cryptography import x509
        from cryptography.x509.oid import NameOID
    except ImportError:
        return len(blocks) > 120

    unknown = 0
    for pem in blocks[:500]:
        try:
            cert = x509.load_pem_x509_certificate(pem)
        except ValueError:
            continue
        org = ""
        for attr in cert.subject:
            if attr.oid == NameOID.ORGANIZATION_NAME:
                org = str(attr.value)
                break
        if not org:
            continue
        is_public = org in PUBLIC_CA_ORGS or any(
            pub in org for pub in PUBLIC_CA_ORGS
        )
        if not is_public:
            unknown += 1
    return unknown > 0


def _sync_probe_tls_inspection(host: str, port: int) -> tuple[bool, str]:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(10)
    try:
        s.connect((host, port))
        req = (
            b"CONNECT www.google.com:443 HTTP/1.1\r\n"
            b"Host: www.google.com:443\r\n"
            b"Proxy-Connection: keep-alive\r\n\r\n"
        )
        s.sendall(req)
        data = b""
        while b"\r\n\r\n" not in data and len(data) < 65536:
            chunk = s.recv(8192)
            if not chunk:
                break
            data += chunk
        head = data.split(b"\r\n\r\n", 1)[0].decode("utf-8", errors="replace")
        if " 200 " not in head and "200 Connection" not in head:
            return False, ""

        ctx = ssl.create_default_context()
        ssl_sock = ctx.wrap_socket(s, server_hostname="www.google.com")
        try:
            cert = ssl_sock.getpeercert()
        finally:
            ssl_sock.close()

        if not cert:
            return False, ""
        issuer: dict[str, str] = {}
        for part in cert.get("issuer", ()):
            for k, v in part:
                issuer[k] = v
        org = (issuer.get("organizationName") or "").strip()
        if not org:
            org = (issuer.get("commonName") or "").strip()

        is_public = bool(org) and any(pub in org for pub in KNOWN_ISSUER_SUBSTR)
        if org and not is_public:
            return True, org
        return False, org
    except (OSError, ssl.SSLError, TimeoutError) as e:
        logger.debug("sync tls inspection: %s", e)
        return False, ""
    finally:
        try:
            s.close()
        except OSError:
            pass
