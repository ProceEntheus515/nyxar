"""
Motor de discovery adaptativo (PROMPTS V7).
Corre en arranque (o bajo demanda) y opcionalmente cada 24h vía cron/orquestador externo.
"""

from __future__ import annotations

import argparse
import asyncio
import copy
import json
import logging
import os
import socket
from dataclasses import asdict, dataclass, field, fields
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("nyxar.discovery.engine")


@dataclass
class InfrastructureMap:
    """
    Mapa de infraestructura detectada. Campos opcionales: no toda red expone todo.
    Sin credenciales: solo hosts, puertos, tipos y rutas no sensibles.
    """

    dns_server: Optional[str] = None
    dns_type: Optional[str] = None
    dns_log_path: Optional[str] = None
    dns_log_format: Optional[str] = None
    dns_api_url: Optional[str] = None

    proxy_present: bool = False
    proxy_host: Optional[str] = None
    proxy_port: Optional[int] = None
    proxy_type: Optional[str] = None
    proxy_auth_required: bool = False
    proxy_log_path: Optional[str] = None
    proxy_log_format: Optional[str] = None
    proxy_tls_bump: bool = False

    firewall_present: bool = False
    firewall_type: Optional[str] = None
    syslog_port: Optional[int] = None
    syslog_protocol: Optional[str] = None
    syslog_format: Optional[str] = None

    wazuh_present: bool = False
    wazuh_version: Optional[str] = None
    wazuh_api_url: Optional[str] = None
    wazuh_api_version: Optional[str] = None
    wazuh_webhook_available: bool = False

    ca_internal: bool = False
    ca_cert_path: Optional[str] = None
    tls_inspection: bool = False

    ad_present: bool = False
    ad_server: Optional[str] = None
    ad_port: int = 389
    ad_domain: Optional[str] = None
    ad_base_dn: Optional[str] = None
    ldap_type: Optional[str] = None

    siem_present: bool = False
    siem_type: Optional[str] = None
    siem_ingest_url: Optional[str] = None
    # Base API para consumo (Splunk mgmt :8089, Elasticsearch :9200, etc.)
    siem_api_url: Optional[str] = None

    network_range: Optional[str] = None
    vlans_detected: list[str] = field(default_factory=list)
    nyxar_vlan: Optional[str] = None

    discovered_at: Optional[str] = None
    discovery_method: str = "auto"
    confidence: float = 0.0


def _infra_from_json(data: dict[str, Any]) -> InfrastructureMap:
    """Rehidrata el mapa ignorando claves desconocidas (versiones futuras del JSON)."""
    template = InfrastructureMap()
    merged: dict[str, Any] = {
        f.name: getattr(template, f.name) for f in fields(InfrastructureMap)
    }
    names = set(merged.keys())
    for k, v in data.items():
        if k in names:
            merged[k] = v
    if merged.get("vlans_detected") is None:
        merged["vlans_detected"] = []
    return InfrastructureMap(**merged)


def infrastructure_map_from_dict(data: dict[str, Any]) -> InfrastructureMap:
    """Rehidrata un mapa desde JSON (snapshots, API)."""
    return _infra_from_json(data)


class DiscoveryEngine:
    """
    Orquesta probes en paralelo; un fallo no aborta el resto.
    """

    MAP_PATH = Path(
        os.environ.get("NYXAR_INFRA_MAP_PATH", ".nyxar_infrastructure_map.json")
    )

    async def run_full_discovery(
        self,
        network_hint: Optional[str] = None,
        verbose: bool = True,
        seed: Optional[InfrastructureMap] = None,
    ) -> InfrastructureMap:
        env_range = (os.environ.get("NETWORK_RANGE") or "").strip()
        if env_range and env_range.lower() != "auto":
            network_hint = network_hint or env_range

        if verbose:
            logger.info("Iniciando deteccion de infraestructura NYXAR")

        infra = copy.deepcopy(seed) if seed else InfrastructureMap()
        infra.discovered_at = datetime.now(timezone.utc).isoformat()
        if seed is None:
            infra.discovery_method = os.environ.get("NYXAR_DISCOVERY_METHOD", "auto")
        else:
            infra.discovery_method = seed.discovery_method or "assisted"

        if network_hint:
            infra.network_range = network_hint
        elif not infra.network_range:
            infra.network_range = await self._detect_network_range()

        if verbose:
            logger.info("Rango de red: %s", infra.network_range)

        from nyxar.discovery.probes.dns_probe import DnsProbe
        from nyxar.discovery.probes.proxy_probe import ProxyProbe
        from nyxar.discovery.probes.firewall_probe import FirewallProbe
        from nyxar.discovery.probes.wazuh_probe import WazuhProbe
        from nyxar.discovery.probes.tls_probe import TlsProbe
        from nyxar.discovery.probes.siem_probe import SiemProbe

        # TLS despues de Proxy para que infra.proxy_* este relleno (inspeccion CONNECT).
        probes_p1 = [
            DnsProbe(infra).run(),
            ProxyProbe(infra).run(),
            FirewallProbe(infra).run(),
            WazuhProbe(infra).run(),
            SiemProbe(infra).run(),
        ]
        names_p1 = ("DNS", "Proxy", "Firewall", "Wazuh", "SIEM")
        results = await asyncio.gather(*probes_p1, return_exceptions=True)
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.warning("Probe %s: %s", names_p1[i], result)
                if verbose:
                    print(f"  [WARN] Probe {names_p1[i]}: {result}")

        tls_res = await asyncio.gather(TlsProbe(infra).run(), return_exceptions=True)
        if isinstance(tls_res[0], Exception):
            logger.warning("Probe TLS: %s", tls_res[0])
            if verbose:
                print(f"  [WARN] Probe TLS: {tls_res[0]}")

        infra.confidence = self._calculate_confidence(infra)
        self._save_map(infra)

        if verbose:
            self._print_summary(infra)

        return infra

    async def _detect_network_range(self) -> str:
        """Heuristica /24 a partir de la ruta por defecto (UDP connect no envia datos)."""
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
        except OSError:
            local_ip = "127.0.0.1"
        finally:
            s.close()
        parts = local_ip.split(".")
        if len(parts) == 4:
            return f"{parts[0]}.{parts[1]}.{parts[2]}.0/24"
        return "0.0.0.0/0"

    def _calculate_confidence(self, infra: InfrastructureMap) -> float:
        scores: list[float] = []
        if infra.dns_server:
            scores.append(0.9 if infra.dns_log_path else 0.5)
        else:
            scores.append(0.0)

        if infra.proxy_present:
            scores.append(0.9 if infra.proxy_log_path else 0.4)
        else:
            scores.append(0.7)

        if infra.syslog_port:
            scores.append(0.9)
        else:
            scores.append(0.3)

        if infra.wazuh_present:
            scores.append(1.0)
        else:
            scores.append(0.5)

        return sum(scores) / len(scores) if scores else 0.0

    def _save_map(self, infra: InfrastructureMap) -> None:
        try:
            self.MAP_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(self.MAP_PATH, "w", encoding="utf-8") as f:
                json.dump(asdict(infra), f, indent=2, default=str)
            logger.info("Mapa guardado en %s", self.MAP_PATH.resolve())
        except OSError as e:
            logger.warning("No se pudo guardar mapa: %s", e)

    def load_existing_map(self) -> Optional[InfrastructureMap]:
        if not self.MAP_PATH.exists():
            return None
        try:
            with open(self.MAP_PATH, encoding="utf-8") as f:
                data = json.load(f)
            return _infra_from_json(data)
        except (OSError, json.JSONDecodeError, TypeError) as e:
            logger.warning("No se pudo cargar mapa existente: %s", e)
            return None

    def _print_summary(self, infra: InfrastructureMap) -> None:
        def status(detected: bool, detail: str = "") -> str:
            mark = "[+]" if detected else "[ ]"
            return f"{mark} {detail if detail else ('detectado' if detected else 'no detectado')}"

        print("\n  --- Infraestructura detectada ---")
        dns_detail = infra.dns_type or infra.dns_server or ""
        print(f"  DNS:       {status(bool(infra.dns_server), dns_detail)}")
        proxy_detail = (
            f"{infra.proxy_host}:{infra.proxy_port} ({infra.proxy_type})"
            if infra.proxy_present and infra.proxy_host
            else ""
        )
        print(f"  Proxy:     {status(infra.proxy_present, proxy_detail)}")
        fw_detail = (
            f"{infra.firewall_type}, syslog:{infra.syslog_port}"
            if infra.firewall_present
            else ""
        )
        print(f"  Firewall:  {status(infra.firewall_present, fw_detail)}")
        print(f"  Wazuh:     {status(infra.wazuh_present, infra.wazuh_version or '')}")
        ca_detail = infra.ca_cert_path or ""
        print(f"  CA interna:{status(infra.ca_internal, ca_detail)}")
        print(f"  AD/LDAP:   {status(infra.ad_present, infra.ad_domain or '')}")
        siem_detail_parts: list[str] = []
        if infra.siem_type:
            siem_detail_parts.append(infra.siem_type)
        if infra.siem_api_url:
            siem_detail_parts.append(f"api {infra.siem_api_url}")
        if infra.siem_ingest_url:
            siem_detail_parts.append(f"ingest {infra.siem_ingest_url}")
        siem_detail = " ".join(siem_detail_parts)
        print(f"  SIEM:      {status(infra.siem_present, siem_detail)}")

        confidence_pct = int(infra.confidence * 100)
        filled = confidence_pct // 10
        bar = "#" * filled + "." * (10 - filled)
        print(f"\n  Confianza del mapa: [{bar}] {confidence_pct}%")

        if infra.confidence < 0.5:
            print("\n  [WARN] Mapa incompleto: considera el asistente:")
            print("    python -m nyxar.discovery.wizard")
        print("  ---------------------------------\n")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    parser = argparse.ArgumentParser(description="NYXAR discovery engine")
    parser.add_argument(
        "--full-discovery",
        action="store_true",
        help="Ejecuta todas las probes y escribe el mapa JSON",
    )
    parser.add_argument(
        "--network",
        default=None,
        help="CIDR opcional (sobrescribe deteccion local)",
    )
    parser.add_argument("--quiet", action="store_true", help="Menos salida en consola")
    args = parser.parse_args()
    if args.full_discovery:
        asyncio.run(
            DiscoveryEngine().run_full_discovery(
                network_hint=args.network,
                verbose=not args.quiet,
            )
        )
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
