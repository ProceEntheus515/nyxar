"""
Publica en events:raw el contrato I01: dict JSON completo de Evento (Normalizer + to_redis_dict).
Reutilizable desde simulador y escenarios sin duplicar lógica de parsers.
"""

from __future__ import annotations

from typing import Optional

from collector.normalizer import Normalizer
from shared.redis_bus import RedisBus


async def publish_raw_log_as_evento(
    redis_bus: RedisBus,
    raw_log: dict,
    source: str,
    normalizer: Optional[Normalizer] = None,
) -> bool:
    """
    Normaliza raw_log con la fuente indicada y publica en STREAM_RAW.
    Retorna False si normalize devolvió None (evento descartado).
    """
    norm = normalizer if normalizer is not None else Normalizer(redis_bus)
    evento = await norm.normalize(raw_log, source)
    if evento is None:
        return False
    await redis_bus.publish_event(redis_bus.STREAM_RAW, evento.to_redis_dict())
    return True
