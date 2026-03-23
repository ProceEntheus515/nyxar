import os
from typing import Literal

from collector.normalizer import Normalizer
from collector.stream_publish import publish_raw_log_as_evento
from shared.logger import get_logger
from shared.redis_bus import RedisBus

logger = get_logger("simulator.attack_scenarios.base")


class BaseAttackScenario:
    def __init__(self, redis_bus: RedisBus, target_persona: dict):
        self.redis_bus = redis_bus
        self.target = target_persona
        self.lab_mode = os.getenv("LAB_MODE", "false").lower() == "true"
        self.time_multiplier = 5 if self.lab_mode else 1
        self._normalizer = Normalizer(redis_bus)

    async def _publish_normalized(self, raw_log: dict, source: str) -> None:
        """Publica en events:raw el Evento normalizado (mismo contrato I01 que el collector)."""
        ok = await publish_raw_log_as_evento(
            self.redis_bus, raw_log, source, self._normalizer
        )
        if not ok:
            logger.debug("Normalizer descartó evento source=%s", source)
    
    async def execute(self, intensity: Literal["baja", "media", "alta"]) -> None:
        raise NotImplementedError
    
    async def cleanup(self) -> None:
        pass
    
    @property
    def description(self) -> str:
        raise NotImplementedError
