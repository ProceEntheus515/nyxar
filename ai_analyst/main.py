"""Punto de entrada del AI Analyst: loop autónomo + heartbeat para observability."""

import asyncio

from autonomous_analyst import AutonomousAnalyst
from shared.logger import get_logger

logger = get_logger("ai_analyst.main")


async def main() -> None:
    analyst = AutonomousAnalyst()
    try:
        await analyst.run()
    finally:
        await analyst.redis_bus.disconnect()
        await analyst.mongo.disconnect()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("AI Analyst detenido por usuario")
