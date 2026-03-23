import os
import json
import random
import asyncio
from typing import Literal
from datetime import datetime
from faker import Faker

from shared.logger import get_logger
from .base import BaseAttackScenario

logger = get_logger("scenario.phishing")
fake = Faker()

class PhishingScenario(BaseAttackScenario):
    """
    1. 3-5 users from same area click malicious domain.
    2. Takes 30-40 min.
    """

    @property
    def description(self) -> str:
        return "Simula una campaña de spear-phishing dentro del mismo departamento. Múltiples usuarios consultan dominios maliciosos nuevos simultáneamente."

    async def execute(self, intensity: Literal["baja", "media", "alta"]) -> None:
        logger.info(f"[PHISHING] Iniciando campaña para objetivo y su área: {self.target['area']}")
        
        # Cargar personas del area
        personas_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "personas.json")
        try:
            with open(personas_path, 'r', encoding='utf-8') as f:
                todas_personas = json.load(f)
        except Exception as e:
            logger.error(f"Fallo cargando personas.json: {e}")
            return
            
        area_targets = [p for p in todas_personas if p["area"] == self.target["area"] and p["id"] != self.target["id"]]
        
        # Seleccionar 3-5 o hasta el límite del area
        num_targets = random.randint(2, 4) # +1 the target itself = 3-5
        selected = random.sample(area_targets, min(num_targets, len(area_targets)))
        victimas = [self.target] + selected
        
        logger.info(f"[PHISHING] {len(victimas)} víctimas seleccionadas en el área {self.target['area']}")
        
        # Generar dominio nuevo (1-2 semanas viejo, tld com o info)
        fake_words = fake.words(nb=2)
        mal_domain = f"login-{'-'.join(fake_words)}." + random.choice(["com", "info"])
        
        logger.info(f"[PHISHING] Vector generado: {mal_domain}")

        # Distribuir consultas en 30-40 mins
        # En LAB_MODE (5x): 30 reals mins son 6 mins simulados. 
        # Pero dormimos en minutos reales para respetar el ratio. 
        # Gap entre consultas: 3 a 15 min simulados => /5 real.
        
        for idx, victima in enumerate(victimas):
            # Pausa de 3 a 15 mins (simulados)
            gap_simulado = random.uniform(3*60, 15*60)
            gap_real = gap_simulado / self.time_multiplier
            
            logger.debug(f"[PHISHING] Esperando {gap_real:.1f}s reales hasta próxima víctima...")
            await asyncio.sleep(gap_real)
            
            # DNS Event
            now = datetime.now()
            ts_str = now.strftime("%b %d %H:%M:%S")
            dns_event = {
                "timestamp": ts_str,
                "client": victima["dispositivo"],
                "domain": mal_domain,
                "type": "A",
                "status": "NOERROR",
                "blocked": False # Dominio nuevo, nunca cae en block
            }
            await self._publish_normalized(dns_event, "dns")
            
            # 60% click (Proxy Event)
            if random.random() <= 0.60:
                proxy_event = {
                    "timestamp": f"{now.timestamp():.3f}",
                    "client_ip": victima["dispositivo"],
                    "method": "GET",
                    "url": f"https://{mal_domain}/auth/login",
                    "status_code": "200",
                    "bytes": "8540",
                    "destination_ip": fake.ipv4()
                }
                await self._publish_normalized(proxy_event, "proxy")
                logger.info(f"[PHISHING] Víctima {victima['id']} ha CAÍDO en el engaño (click).")
            else:
                logger.info(f"[PHISHING] Víctima {victima['id']} resolvió DNS pero NO ingresó a la web.")
                
        logger.info("[PHISHING] Campaña finalizada.")
