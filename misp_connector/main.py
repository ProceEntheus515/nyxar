"""
Orquestador del conector MISP: conexión con reintentos y tareas ingestor + contributor.
"""

import asyncio

from shared.logger import get_logger

from misp_connector.client import MISPClient
from misp_connector import contributor
from misp_connector.ingestor import MISPIngestor

logger = get_logger("misp_connector.main")

RETRY_CONNECT_S = 300


async def main() -> None:
    client = MISPClient()

    while True:
        if await client.connect():
            break
        logger.error("No se pudo conectar a MISP. Revisar MISP_URL y MISP_API_KEY.")
        await asyncio.sleep(RETRY_CONNECT_S)

    ingestor = MISPIngestor()
    await asyncio.gather(
        ingestor.start(client),
        contributor.start(client),
    )


if __name__ == "__main__":
    asyncio.run(main())
