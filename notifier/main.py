"""
Proceso worker: `python -m notifier.main` (tras configurar Redis/Mongo y NOTIFY_*).
"""

import asyncio

from shared.logger import get_logger
from notifier.engine import NotificationEngine

logger = get_logger("notifier.main")


async def _run() -> None:
    eng = NotificationEngine()
    await eng.start()


if __name__ == "__main__":
    try:
        asyncio.run(_run())
    except KeyboardInterrupt:
        logger.info("NotificationEngine detenido por usuario")
