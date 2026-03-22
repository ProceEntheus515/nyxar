"""
Heartbeat en Redis para que observability marque servicios vivos (TTL corto).
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from shared.logger import get_logger
from shared.redis_bus import RedisBus

logger = get_logger("shared.heartbeat")


async def heartbeat_loop(
    redis_bus: RedisBus,
    nombre: str,
    interval_s: int = 30,
    ttl_s: int = 90,
) -> None:
    """
    Publica heartbeat:{nombre} con JSON {ts} cada interval_s segundos.
    TTL mayor que el intervalo para tolerar jitter.
    """
    key = f"heartbeat:{nombre}"
    while True:
        try:
            if redis_bus.client:
                await redis_bus.cache_set(
                    key,
                    {"ts": datetime.now(timezone.utc).isoformat()},
                    ttl_s,
                )
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.warning("heartbeat %s: %s", nombre, e)
        await asyncio.sleep(interval_s)
