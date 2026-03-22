"""Validacion de IPs para playbooks (RFC1918, lista protegida)."""

from __future__ import annotations

import ipaddress
import os
import re
from typing import FrozenSet, Optional


def is_rfc1918(ip: str) -> bool:
    """True si la IP es privada RFC1918 (10/8, 172.16/12, 192.168/16)."""
    try:
        addr = ipaddress.ip_address(ip.strip())
    except ValueError:
        return False
    return addr.is_private


def parse_protected_ips() -> FrozenSet[str]:
    """Lee PROTECTED_IPS del entorno (CSV)."""
    raw = (os.getenv("PROTECTED_IPS") or "").strip()
    if not raw:
        return frozenset()
    parts = re.split(r"[\s,;]+", raw)
    return frozenset(p.strip() for p in parts if p.strip())


def is_protected_ip(ip: str) -> bool:
    """True si la IP esta en PROTECTED_IPS (comparacion como string normalizada)."""
    needle = (ip or "").strip()
    if not needle:
        return False
    return needle in parse_protected_ips()


def normalize_ip(ip: str) -> Optional[str]:
    """Devuelve representacion canonica de IPv4/IPv6 o None si invalida."""
    try:
        return str(ipaddress.ip_address((ip or "").strip()))
    except ValueError:
        return None


def firewall_url(base: str, path: str) -> str:
    """Une base URL y path sin duplicar barras."""
    b = (base or "").strip().rstrip("/") + "/"
    p = (path or "").strip().lstrip("/")
    return b + p
