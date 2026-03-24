"""
Adaptadores: traducen InfrastructureMap a sugerencias de configuracion (sin secretos).
"""

from nyxar.discovery.adapters.dns_adapter import DnsAdapter, suggest_dns_env
from nyxar.discovery.adapters.firewall_adapter import suggest_firewall_env
from nyxar.discovery.adapters.proxy_adapter import ProxyAdapter, suggest_proxy_env
from nyxar.discovery.adapters.siem_adapter import suggest_siem_env
from nyxar.discovery.adapters.tls_adapter import suggest_tls_env

__all__ = [
    "DnsAdapter",
    "ProxyAdapter",
    "suggest_dns_env",
    "suggest_firewall_env",
    "suggest_proxy_env",
    "suggest_siem_env",
    "suggest_tls_env",
]
