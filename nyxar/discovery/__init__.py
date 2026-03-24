"""
Discovery adaptativo: NYXAR detecta infraestructura disponible sin exigir que la red se adapte a él.

Los imports de engine son diferidos para evitar ciclo probes -> engine -> __init__.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

__all__ = ["DiscoveryEngine", "InfrastructureMap"]

if TYPE_CHECKING:
    from nyxar.discovery.engine import DiscoveryEngine, InfrastructureMap


def __getattr__(name: str):
    if name in ("DiscoveryEngine", "InfrastructureMap"):
        from nyxar.discovery import engine as _engine

        return getattr(_engine, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
