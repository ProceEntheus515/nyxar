"""
Adaptador firewall / syslog: variables sugeridas, instrucciones para admin, receptor (D04).
"""

from __future__ import annotations

from typing import Any

from nyxar.discovery.engine import InfrastructureMap
from nyxar.discovery.syslog.receiver import SyslogReceiver


def suggest_firewall_env(infra: InfrastructureMap) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if infra.firewall_type:
        out["NYXAR_FIREWALL_TYPE"] = infra.firewall_type
    if infra.syslog_port:
        out["NYXAR_SYSLOG_PORT"] = str(infra.syslog_port)
    if infra.syslog_protocol:
        out["NYXAR_SYSLOG_PROTOCOL"] = infra.syslog_protocol
    if infra.syslog_format:
        out["NYXAR_SYSLOG_FORMAT"] = infra.syslog_format
    return out


def generate_firewall_config_instructions(nyxar_ip: str, fw_type: str) -> str:
    """
    Texto listo para entregar al administrador del firewall (Setup Wizard D08).
    nyxar_ip: IP alcanzable desde el firewall (NYXAR escucha UDP/TCP alli).
    """
    fw = (fw_type or "generic").strip().lower()
    instructions: dict[str, str] = {
        "fortinet": f"""
En FortiGate, ir a Log & Report > Log Settings:
  Syslog Server: {nyxar_ip}
  Port: 514
  Protocol: UDP
  Facility: local7
  Log Level: information
""",
        "paloalto": f"""
En Palo Alto, ir a Device > Server Profiles > Syslog:
  Name: NYXAR
  Syslog Server: {nyxar_ip}
  Port: 514
  Transport: UDP
  Format: BSD (RFC 3164)
Luego en Device > Log Settings, activar el perfil NYXAR.
""",
        "pfsense": f"""
En pfSense, ir a Status > System Logs > Settings:
  Enable Remote Logging: checked
  Remote log servers: {nyxar_ip}
  Remote Syslog Contents: Firewall Events
""",
        "opnsense": f"""
En OPNsense, ir a System > Settings > Logging / Targets:
  Agregar destino syslog remoto: {nyxar_ip}
  Puerto: 514
  Protocolo: UDP
  Seleccionar categorias de firewall segun politica local.
""",
        "generic": f"""
Configurar el firewall para enviar syslog UDP a:
  Destino: {nyxar_ip}
  Puerto: 514
  Protocolo: UDP
  Formato: CEF (preferido) o syslog RFC 3164 / RFC 5424
Opcional TCP/TLS al puerto 6514 si NYXAR tiene certificado (NYXAR_SYSLOG_TLS_*).
""",
    }
    if "forti" in fw or "fortigate" in fw:
        return instructions["fortinet"].strip()
    if "palo" in fw or "pan-" in fw:
        return instructions["paloalto"].strip()
    if "pfsense" in fw or "pf sense" in fw:
        return instructions["pfsense"].strip()
    if "opnsense" in fw or "opn sense" in fw:
        return instructions["opnsense"].strip()
    return instructions["generic"].strip()
