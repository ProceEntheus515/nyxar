"""
Ejecutar: python -m nyxar.discovery.syslog (desde la raiz del repo, PYTHONPATH=.).
Requiere REDIS_URL y modulos api/ disponibles.
"""

from __future__ import annotations

import asyncio
import logging
import sys


async def _run() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )
    from shared.redis_bus import RedisBus

    from nyxar.discovery.engine import DiscoveryEngine, InfrastructureMap
    from nyxar.discovery.syslog.receiver import SyslogReceiver

    bus = RedisBus()
    await bus.connect()
    infra = DiscoveryEngine().load_existing_map() or InfrastructureMap()
    recv = SyslogReceiver(bus, infra)
    await recv.start()


def main() -> None:
    try:
        asyncio.run(_run())
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    main()
