"""Utilidades de red para el wizard (IP local alcanzable)."""

from __future__ import annotations

import socket


def get_local_ipv4() -> str:
    """IPv4 local usada para salida (misma heuristica que DiscoveryEngine)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()
