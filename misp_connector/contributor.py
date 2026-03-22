"""
Publicación de IOCs propios hacia MISP (implementación completa en prompt V03).
"""

import asyncio

from shared.logger import get_logger

from misp_connector.client import MISPClient

logger = get_logger("misp_connector.contributor")

_IDLE_INTERVAL_S = 300


async def start(client: MISPClient) -> None:
    """
    Si MISP_CONTRIBUTE no está activo, termina de inmediato.
    Si está activo, mantiene un bucle idle hasta la lógica de contribución (V03).
    """
    if not client.contribute:
        logger.info("MISP contributor deshabilitado (MISP_CONTRIBUTE=false)")
        return

    logger.info("MISP contributor iniciado (stub V01, MISP_CONTRIBUTE=true)")
    while True:
        await asyncio.sleep(_IDLE_INTERVAL_S)
        logger.info("MISP contributor en espera de implementación V03 (stub activo)")
