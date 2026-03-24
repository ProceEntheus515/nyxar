"""
Setup asistido (ASSISTED): preguntas minimas y fusion con el mapa existente.
No almacena contrasenas; solo hosts, puertos y tipos.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys

from nyxar.discovery.engine import DiscoveryEngine, InfrastructureMap

logger = logging.getLogger("nyxar.discovery.wizard")


def _prompt(label: str, default: str = "") -> str:
    try:
        raw = input(f"{label} [{default}]: ").strip()
    except EOFError:
        return default
    return raw if raw else default


def run_interactive() -> InfrastructureMap:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    engine = DiscoveryEngine()
    existing = engine.load_existing_map()
    infra = existing or InfrastructureMap()
    infra.discovery_method = "assisted"

    print("NYXAR Setup Wizard (modo asistido)")
    print("Enter acepta el valor entre corchetes.\n")

    cidr = _prompt("Rango de red (CIDR)", infra.network_range or "")
    if cidr:
        infra.network_range = cidr

    dns = _prompt("Servidor DNS (IP o vacio)", infra.dns_server or "")
    if dns:
        infra.dns_server = dns
        infra.dns_type = _prompt("Tipo DNS (pihole/bind9/windows_dns/other)", infra.dns_type or "other")

    proxy = _prompt("Hay proxy HTTP/HTTPS? (s/n)", "n").lower()
    if proxy in ("s", "si", "y", "yes"):
        infra.proxy_present = True
        infra.proxy_host = _prompt("Host del proxy", infra.proxy_host or "")
        port_s = _prompt("Puerto", str(infra.proxy_port or 8080))
        if port_s.isdigit():
            infra.proxy_port = int(port_s)
        infra.proxy_type = _prompt("Tipo (squid/nginx/other)", infra.proxy_type or "other")

    wazuh = _prompt("URL API Wazuh (vacío si no aplica)", infra.wazuh_api_url or "")
    if wazuh:
        infra.wazuh_present = True
        infra.wazuh_api_url = wazuh.rstrip("/")

    siem = _prompt("URL ingest SIEM (sin tokens en la URL)", infra.siem_ingest_url or "")
    if siem:
        infra.siem_present = True
        infra.siem_ingest_url = siem
        infra.siem_type = _prompt("Tipo (splunk/elastic/qradar/other)", infra.siem_type or "other")

    return asyncio.run(
        engine.run_full_discovery(
            network_hint=infra.network_range,
            verbose=True,
            seed=infra,
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="NYXAR discovery wizard (asistido)")
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Solo ejecuta discovery automatico sin preguntas",
    )
    args = parser.parse_args()
    if args.non_interactive:
        asyncio.run(DiscoveryEngine().run_full_discovery(verbose=True))
        return
    if not sys.stdin.isatty():
        logger.warning("STDIN no es TTY; ejecutando discovery automatico")
        asyncio.run(DiscoveryEngine().run_full_discovery(verbose=True))
        return
    run_interactive()


if __name__ == "__main__":
    main()
