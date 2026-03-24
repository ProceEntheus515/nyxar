"""
Snapshots del mapa de infraestructura (D09): historial, diff y reporte redactado para soporte.
El mapa actual no incluye credenciales; el guardado defensivo elimina claves sensibles si existieran.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from nyxar.discovery.engine import (
    DiscoveryEngine,
    InfrastructureMap,
    infrastructure_map_from_dict,
)

logger = logging.getLogger("nyxar.discovery.snapshot")

# Claves que nunca deben aparecer en JSON compartido o snapshots (defensivo).
_SENSITIVE_MAP_KEYS = frozenset(
    {
        "ad_password",
        "proxy_password",
        "wazuh_api_token",
        "wazuh_api_pass",
        "siem_token",
    }
)

_COMPARE_FIELDS = (
    "dns_server",
    "dns_type",
    "proxy_present",
    "proxy_host",
    "proxy_port",
    "firewall_present",
    "firewall_type",
    "wazuh_present",
    "ca_internal",
    "tls_inspection",
    "siem_present",
    "siem_type",
    "ad_present",
    "ldap_type",
    "network_range",
)


class ConfigSnapshot:
    """Persistencia versionada del InfrastructureMap y utilidades de diff / reporte."""

    def __init__(
        self,
        snapshot_dir: Optional[Path] = None,
        current_map_path: Optional[Path] = None,
    ) -> None:
        raw_dir = (os.environ.get("NYXAR_SNAPSHOT_DIR") or "").strip()
        self.snapshot_dir = snapshot_dir or Path(raw_dir or ".nyxar_snapshots")
        self.current_map_path = current_map_path or DiscoveryEngine.MAP_PATH

    def save_snapshot(self, infra: InfrastructureMap) -> str:
        """Guarda map_{timestamp}.json en snapshot_dir. Retorna el id (timestamp)."""
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)
        snapshot_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        snapshot_path = self.snapshot_dir / f"map_{snapshot_id}.json"
        data = asdict(infra)
        for k in _SENSITIVE_MAP_KEYS:
            data.pop(k, None)
        with open(snapshot_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)
        logger.info("Snapshot guardado: %s", snapshot_path.resolve())
        return snapshot_id

    @staticmethod
    def compare_snapshots(
        snapshot_a: InfrastructureMap,
        snapshot_b: InfrastructureMap,
    ) -> dict[str, dict[str, Any]]:
        """Compara dos mapas; valores distintos bajo 'antes' / 'ahora'."""
        changes: dict[str, dict[str, Any]] = {}
        for field in _COMPARE_FIELDS:
            val_a = getattr(snapshot_a, field, None)
            val_b = getattr(snapshot_b, field, None)
            if val_a != val_b:
                changes[field] = {"antes": val_a, "ahora": val_b}
        return changes

    @staticmethod
    def generate_redacted_report(infra: InfrastructureMap) -> str:
        """
        JSON sin hosts ni URLs internas: solo presencia y tipos (compartir con soporte).
        """
        version = (os.environ.get("NYXAR_VERSION") or "unknown").strip()
        report = {
            "nyxar_version": version,
            "discovery_date": infra.discovered_at,
            "confidence": f"{int(infra.confidence * 100)}%",
            "infrastructure": {
                "has_dns": bool(infra.dns_server),
                "dns_type": infra.dns_type,
                "has_proxy": infra.proxy_present,
                "proxy_type": infra.proxy_type,
                "has_tls_inspection": infra.tls_inspection,
                "has_internal_ca": infra.ca_internal,
                "has_wazuh": infra.wazuh_present,
                "wazuh_version": infra.wazuh_version,
                "has_ad": infra.ad_present,
                "ldap_type": infra.ldap_type,
                "has_siem": infra.siem_present,
                "siem_type": infra.siem_type,
                "has_firewall_hint": infra.firewall_present,
                "firewall_type": infra.firewall_type,
                "discovery_method": infra.discovery_method,
            },
        }
        return json.dumps(report, indent=2, ensure_ascii=False)

    def load_map_file(self, path: Path) -> InfrastructureMap:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return infrastructure_map_from_dict(data)


def _cmd_save(args: argparse.Namespace) -> None:
    engine = DiscoveryEngine()
    existing = engine.load_existing_map()
    if existing is None:
        raise SystemExit("No existe mapa actual; ejecuta discovery primero.")
    snap = ConfigSnapshot()
    sid = snap.save_snapshot(existing)
    print(sid)


def _cmd_compare(args: argparse.Namespace) -> None:
    snap = ConfigSnapshot()
    a = snap.load_map_file(Path(args.a))
    b = snap.load_map_file(Path(args.b))
    diff = ConfigSnapshot.compare_snapshots(a, b)
    print(json.dumps(diff, indent=2, default=str, ensure_ascii=False))


def _cmd_redact(args: argparse.Namespace) -> None:
    snap = ConfigSnapshot()
    path = Path(args.map_path) if args.map_path else snap.current_map_path
    if not path.exists():
        raise SystemExit(f"No se encontro: {path}")
    infra = snap.load_map_file(path)
    print(ConfigSnapshot.generate_redacted_report(infra))


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    parser = argparse.ArgumentParser(description="NYXAR config snapshot (D09)")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_save = sub.add_parser("save", help="Guarda snapshot del mapa actual")
    p_save.set_defaults(func=_cmd_save)

    p_cmp = sub.add_parser("compare", help="Compara dos archivos JSON de mapa")
    p_cmp.add_argument("a", type=str)
    p_cmp.add_argument("b", type=str)
    p_cmp.set_defaults(func=_cmd_compare)

    p_red = sub.add_parser("redact", help="Imprime reporte redactado (stdout)")
    p_red.add_argument(
        "map_path",
        type=str,
        nargs="?",
        default=None,
        help="Ruta al JSON (por defecto mapa actual)",
    )
    p_red.set_defaults(func=_cmd_redact)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
