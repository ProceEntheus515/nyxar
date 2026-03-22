import asyncio
from shared.logger import get_logger
from shared.redis_bus import RedisBus

from .phishing import PhishingScenario
from .ransomware import RansomwareScenario
from .dns_tunneling import DnsTunnelingScenario
from .lateral_movement import LateralMovementScenario
from .exfiltration import ExfiltrationScenario

logger = get_logger("simulator.attack_scenarios")

SCENARIOS = {
    "phishing": PhishingScenario,
    "ransomware": RansomwareScenario,
    "dns_tunneling": DnsTunnelingScenario,
    "lateral_movement": LateralMovementScenario,
    "exfiltration": ExfiltrationScenario,
}

async def run_scenario(name: str, target_persona: dict, intensity: str, redis_bus: RedisBus) -> None:
    if name not in SCENARIOS:
        logger.error(f"Escenario {name} no encontrado.")
        return
        
    scenario_class = SCENARIOS[name]
    scenario = scenario_class(redis_bus=redis_bus, target_persona=target_persona)
    
    logger.info(f"Iniciando escenario: {name} | Target: {target_persona.get('id')} | Intensity: {intensity}")
    logger.info(f"Descripción: {scenario.description}")
    
    try:
        await scenario.execute(intensity=intensity)
    except asyncio.CancelledError:
        logger.info(f"Escenario {name} cancelado antes de terminar.")
    except Exception as e:
        logger.error(f"Fallo en escenario {name}: {e}")
    finally:
        await scenario.cleanup()
        logger.info(f"Escenario {name} finalizado y limpiado.")
