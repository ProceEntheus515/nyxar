import os
from typing import Literal
from shared.redis_bus import RedisBus

class BaseAttackScenario:
    def __init__(self, redis_bus: RedisBus, target_persona: dict):
        self.redis_bus = redis_bus
        self.target = target_persona
        self.lab_mode = os.getenv("LAB_MODE", "false").lower() == "true"
        self.time_multiplier = 5 if self.lab_mode else 1
    
    async def execute(self, intensity: Literal["baja", "media", "alta"]) -> None:
        raise NotImplementedError
    
    async def cleanup(self) -> None:
        pass
    
    @property
    def description(self) -> str:
        raise NotImplementedError
