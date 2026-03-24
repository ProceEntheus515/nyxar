"""
Setup Wizard (D08): auto-discovery con Rich y preguntas minimas.
Credenciales solo hacia .env en disco, no en InfrastructureMap ni en el JSON del mapa.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Confirm, Prompt
from rich.table import Table

from nyxar.discovery.adapters.firewall_adapter import generate_firewall_config_instructions
from nyxar.discovery.engine import DiscoveryEngine, InfrastructureMap
from nyxar.discovery.wizard_env import format_env_block, merge_suggested_env
from nyxar.discovery.wizard_net import get_local_ipv4

logger = logging.getLogger("nyxar.discovery.wizard")

console = Console()
DEFAULT_ENV_PATH = Path(".env")


def _generate_env_config(infra: InfrastructureMap) -> str:
    return format_env_block(merge_suggested_env(infra))


def _save_to_env(config_body: str, secret_lines: list[str], env_path: Path) -> None:
    """Anexa bloque al .env local; no sobrescribe el archivo completo."""
    extra = "\n".join(secret_lines).strip()
    block = config_body.rstrip() + "\n"
    if extra:
        block += "\n# --- secretos (wizard; permisos restrictivos recomendados) ---\n"
        block += extra + "\n"
    marker = "\n# --- nyxar wizard ---\n"
    payload = marker + block
    env_path.parent.mkdir(parents=True, exist_ok=True)
    if env_path.exists():
        existing = env_path.read_text(encoding="utf-8")
        if "nyxar wizard" in existing.lower():
            console.print(
                "[yellow]El archivo .env ya contiene un bloque del wizard; "
                "se anexa otro bloque. Revisa duplicados de variables.[/yellow]"
            )
        with open(env_path, "a", encoding="utf-8") as f:
            f.write(payload)
    else:
        env_path.write_text(block.lstrip(), encoding="utf-8")


def _show_discovery_results(infra: InfrastructureMap) -> None:
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Componente", style="dim")
    table.add_column("Estado")
    table.add_column("Detalle", style="dim")

    def row(name: str, detected: bool, detail: str = "") -> None:
        mark = "[green]si[/green]" if detected else "[dim]no[/dim]"
        status = "detectado" if detected else "no detectado"
        table.add_row(name, f"{mark}  {status}", detail)

    dns_detail = (
        f"{infra.dns_type or ''} — {infra.dns_server}"
        if infra.dns_server
        else ""
    )
    row("DNS", bool(infra.dns_server), dns_detail.strip(" —"))
    proxy_detail = (
        f"{infra.proxy_host}:{infra.proxy_port} ({infra.proxy_type})"
        if infra.proxy_present and infra.proxy_host
        else ""
    )
    row("Proxy", infra.proxy_present, proxy_detail)
    row(
        "TLS Inspection",
        infra.tls_inspection,
        "proxy re-firma certificados" if infra.tls_inspection else "",
    )
    row("CA interna", infra.ca_internal, infra.ca_cert_path or "")
    row("Wazuh", infra.wazuh_present, infra.wazuh_api_url or "")
    row("Active Directory", infra.ad_present, infra.ad_domain or "")
    siem_bits = " ".join(
        x
        for x in (
            infra.siem_type or "",
            f"api {infra.siem_api_url}" if infra.siem_api_url else "",
            f"ingest {infra.siem_ingest_url}" if infra.siem_ingest_url else "",
        )
        if x
    )
    row("SIEM existente", infra.siem_present, siem_bits)
    fw_detail = (
        f"{infra.firewall_type or ''}, syslog:{infra.syslog_port or ''}"
        if infra.firewall_present
        else ""
    )
    row("Firewall", infra.firewall_present, fw_detail)

    console.print(table)


async def _ask_missing_info(infra: InfrastructureMap) -> tuple[InfrastructureMap, list[str]]:
    secret_lines: list[str] = []

    if not infra.dns_server:
        console.print("[yellow]No se detecto servidor DNS automaticamente.[/yellow]")
        dns = Prompt.ask("IP del servidor DNS interno (Enter para omitir)", default="").strip()
        if dns:
            infra.dns_server = dns
            if not infra.dns_type:
                infra.dns_type = "other"

    if infra.proxy_present and infra.proxy_auth_required:
        console.print("[yellow]El proxy requiere autenticacion.[/yellow]")
        console.print("NYXAR necesita una cuenta de servicio de solo lectura.")
        proxy_user = Prompt.ask("Usuario del proxy (p. ej. usuario@dominio)")
        proxy_pass = Prompt.ask("Contrasena del proxy", password=True)
        secret_lines.append(f"HTTP_PROXY_USER={proxy_user}")
        secret_lines.append(f"HTTP_PROXY_PASSWORD={proxy_pass}")
        secret_lines.append(f"HTTPS_PROXY_USER={proxy_user}")
        secret_lines.append(f"HTTPS_PROXY_PASSWORD={proxy_pass}")

    if infra.tls_inspection and not infra.ca_cert_path:
        console.print(
            "[yellow]Se detecto inspeccion TLS pero no la ruta al certificado de la CA interna.[/yellow]"
        )
        ca_path = Prompt.ask(
            "Ruta al certificado de la CA interna (.pem o .crt)",
            default="",
        ).strip()
        if ca_path:
            infra.ca_cert_path = ca_path

    if infra.wazuh_present and infra.wazuh_api_url:
        console.print("[green]Wazuh detectado.[/green] Credenciales de API de solo lectura.")
        wazuh_user = Prompt.ask("Usuario API Wazuh", default="wazuh")
        wazuh_pass = Prompt.ask("Contrasena API Wazuh", password=True)
        secret_lines.append(f"WAZUH_API_USER={wazuh_user}")
        secret_lines.append(f"WAZUH_API_PASS={wazuh_pass}")
        secret_lines.append(f"WAZUH_API_URL={infra.wazuh_api_url.rstrip('/')}")

    if infra.ad_present:
        console.print("[green]Active Directory detectado.[/green]")
        console.print("Cuenta de solo lectura para resolver identidades (formato del conector AD).")
        ad_user = Prompt.ask("Usuario AD (DN o UPN segun tu conector)", default="").strip()
        ad_pass = Prompt.ask("Contrasena de la cuenta de servicio", password=True)
        if ad_user:
            secret_lines.append(f"AD_USER={ad_user}")
            if ad_pass:
                secret_lines.append(f"AD_PASSWORD={ad_pass}")
        if infra.ad_domain and not any("AD_DOMAIN=" in s for s in secret_lines):
            secret_lines.append(f"AD_DOMAIN={infra.ad_domain}")

    return infra, secret_lines


async def run_wizard(env_path: Optional[Path] = None) -> InfrastructureMap:
    """
    Wizard interactivo: auto-detecta, pregunta huecos, sugiere .env (sin guardar secretos en el mapa).
    """
    target_env = env_path or DEFAULT_ENV_PATH

    console.print(
        Panel.fit(
            "[cyan]NYXAR[/cyan] — [white]Configuracion de despliegue[/white]\n"
            "[dim]Discovery adaptativo y preguntas minimas.[/dim]",
            border_style="cyan",
        )
    )
    console.print()

    engine = DiscoveryEngine()
    logging.getLogger("nyxar.discovery.engine").setLevel(logging.WARNING)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Detectando infraestructura de red...", total=None)
        infra = await engine.run_full_discovery(verbose=False)
        progress.update(task, description="Discovery completado")

    console.print()
    _show_discovery_results(infra)
    console.print()

    infra, secret_lines = await _ask_missing_info(infra)
    engine._save_map(infra)

    config = _generate_env_config(infra)
    console.print(
        Panel(
            config,
            title="[cyan]Configuracion sugerida (.env)[/cyan]",
            border_style="dim",
        )
    )

    save = Confirm.ask("\nGuardar esta configuracion en .env?", default=True)
    if save:
        _save_to_env(config, secret_lines, target_env)
        console.print(f"[green]Listo: anexado en {target_env.resolve()}[/green]")

    # Si no hubo firewall en discovery, ofrecer guia para apuntar syslog a NYXAR.
    if not infra.firewall_present:
        show_fw = Confirm.ask(
            "\nVer instrucciones para configurar syslog en el firewall?",
            default=True,
        )
        if show_fw:
            fw_type = Prompt.ask(
                "Tipo de firewall",
                choices=["fortinet", "paloalto", "pfsense", "cisco", "generic"],
                default="generic",
            )
            nyxar_ip = get_local_ipv4()
            instructions = generate_firewall_config_instructions(nyxar_ip, fw_type)
            console.print(
                Panel(
                    instructions,
                    title=f"[yellow]Syslog hacia NYXAR — {fw_type}[/yellow]",
                )
            )

    console.print()
    console.print("[cyan]NYXAR listo para desplegar.[/cyan]")
    console.print(f"   Confianza del mapa: {int(infra.confidence * 100)}%")
    console.print()
    console.print("   Para arrancar:")
    console.print("   [dim]docker compose --profile lab up[/dim]  (laboratorio)")
    console.print("   [dim]docker compose -f docker-compose.prod.yml up[/dim]  (produccion)")

    return infra


def run_interactive() -> InfrastructureMap:
    """Compatibilidad: modo asistido previo (preguntas antes del discovery)."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    engine = DiscoveryEngine()
    existing = engine.load_existing_map()
    infra = existing or InfrastructureMap()
    infra.discovery_method = "assisted"

    console.print("NYXAR Setup Wizard (modo asistido clasico)")
    console.print("Enter acepta el valor entre corchetes.\n")

    def _legacy_prompt(label: str, default: str = "") -> str:
        try:
            raw = input(f"{label} [{default}]: ").strip()
        except EOFError:
            return default
        return raw if raw else default

    cidr = _legacy_prompt("Rango de red (CIDR)", infra.network_range or "")
    if cidr:
        infra.network_range = cidr

    dns = _legacy_prompt("Servidor DNS (IP o vacio)", infra.dns_server or "")
    if dns:
        infra.dns_server = dns
        infra.dns_type = _legacy_prompt(
            "Tipo DNS (pihole/bind9/windows_dns/other)",
            infra.dns_type or "other",
        )

    proxy = _legacy_prompt("Hay proxy HTTP/HTTPS? (s/n)", "n").lower()
    if proxy in ("s", "si", "y", "yes"):
        infra.proxy_present = True
        infra.proxy_host = _legacy_prompt("Host del proxy", infra.proxy_host or "")
        port_s = _legacy_prompt("Puerto", str(infra.proxy_port or 8080))
        if port_s.isdigit():
            infra.proxy_port = int(port_s)
        infra.proxy_type = _legacy_prompt("Tipo (squid/nginx/other)", infra.proxy_type or "other")

    wazuh = _legacy_prompt("URL API Wazuh (vacio si no aplica)", infra.wazuh_api_url or "")
    if wazuh:
        infra.wazuh_present = True
        infra.wazuh_api_url = wazuh.rstrip("/")

    siem = _legacy_prompt("URL ingest SIEM (sin tokens en la URL)", infra.siem_ingest_url or "")
    if siem:
        infra.siem_present = True
        infra.siem_ingest_url = siem
        infra.siem_type = _legacy_prompt("Tipo (splunk/elastic/qradar/other)", infra.siem_type or "other")

    return asyncio.run(
        engine.run_full_discovery(
            network_hint=infra.network_range,
            verbose=True,
            seed=infra,
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="NYXAR discovery setup wizard (D08)")
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Solo ejecuta discovery automatico sin preguntas",
    )
    parser.add_argument(
        "--classic",
        action="store_true",
        help="Modo asistido anterior (preguntas antes del discovery)",
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        default=None,
        help="Ruta del .env donde anexar (por defecto ./.env)",
    )
    args = parser.parse_args()

    if args.non_interactive:
        logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
        asyncio.run(DiscoveryEngine().run_full_discovery(verbose=True))
        return

    if not sys.stdin.isatty():
        logger.warning("STDIN no es TTY; ejecutando discovery automatico")
        logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
        asyncio.run(DiscoveryEngine().run_full_discovery(verbose=True))
        return

    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s")

    if args.classic:
        run_interactive()
        return

    try:
        asyncio.run(run_wizard(env_path=args.env_file))
    except KeyboardInterrupt:
        console.print("\n[yellow]Wizard cancelado.[/yellow]")
        sys.exit(130)


if __name__ == "__main__":
    main()
