"""Punto de entrada del simulador. Orquesta el generator (modo lab/prod) y heartbeat en Redis."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

from shared.logger import get_logger
from shared.redis_bus import RedisBus
from shared.heartbeat import heartbeat_loop
from simulator.generator import TrafficGenerator

logger = get_logger("simulator.main")


async def _run() -> None:
    base = Path(__file__).resolve().parent
    personas_path = base / "personas.json"
    with open(personas_path, encoding="utf-8") as f:
        personas = json.load(f)

    redis_bus = RedisBus()
    await redis_bus.connect()

    gen = TrafficGenerator(personas, redis_bus)
    tasks = [
        asyncio.create_task(heartbeat_loop(redis_bus, "simulator"), name="simulator-hb"),
        asyncio.create_task(gen.run(), name="simulator-generator"),
    ]
    logger.info("Simulador arrancado (heartbeat:simulator + TrafficGenerator)")
    try:
        await asyncio.gather(*tasks)
    except asyncio.CancelledError:
        for t in tasks:
            t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        raise


if __name__ == "__main__":
    try:
        asyncio.run(_run())
    except KeyboardInterrupt:
        logger.info("Simulador detenido por usuario")
        sys.exit(0)
