import asyncio
import random
import secrets
import base64
from typing import Literal
from datetime import datetime

from shared.logger import get_logger
from .base import BaseAttackScenario

logger = get_logger("scenario.dns_tunneling")

class DnsTunnelingScenario(BaseAttackScenario):

    @property
    def description(self) -> str:
        return "Simula DNS Tunneling: exfiltración sigilosa de datos codificados en subdominios."

    def _generate_payload(self) -> str:
        # Entre 40 y 60 chars. Cada byte en base32 es ~1.6 chars.
        # 30 bytes = 48 chars b32
        data = secrets.token_bytes(random.randint(25, 35))
        encoded = base64.b32encode(data).decode('utf-8').lower().rstrip("=")
        # Partimos el payload grande y un sufijo aleatorio de 8 chars
        return f"{encoded}.{secrets.token_hex(4)}"

    async def execute(self, intensity: Literal["baja", "media", "alta"]) -> None:
        logger.info(f"[DNS TUNNELING] Iniciando exfiltración sorda desde {self.target['dispositivo']}")
        
        base_domain = "telemetry-metrics-aws.com"
        # Duración simulada: 2 a 4 horas -> 120-240 minutos simulados
        duracion_real = random.randint(120*60, 240*60) / self.time_multiplier
        logger.info(f"[DNS TUNNELING] Duración real calculada: {duracion_real:.0f}s (Multi: {self.time_multiplier}x)")
        
        end_time = asyncio.get_event_loop().time() + duracion_real
        bytes_exfiltrados = 0
        iteration = 1
        
        while asyncio.get_event_loop().time() < end_time:
            now = datetime.now()
            subdomain = self._generate_payload()
            full_domain = f"{subdomain}.{base_domain}"
            
            # DNS query (txt/a)
            dns_event = {
                "timestamp": now.strftime("%b %d %H:%M:%S"),
                "client": self.target["dispositivo"],
                "domain": full_domain,
                "type": "TXT",
                "status": "NOERROR",
                "blocked": False
            }
            await self._publish_normalized(dns_event, "dns")
            
            bytes_exfiltrados += len(subdomain)
            
            # Ajuste de payload dinámico
            if iteration % 50 == 0:
                logger.debug(f"[DNS TUNNELING] Iteración {iteration}: {bytes_exfiltrados} bytes filtrados vía DNS")
                
            iteration += 1
            
            # Frecuencia: 1 consulta cada 15-30 segundos simulados
            gap_simulado = random.uniform(15, 30)
            if intensity == "baja":
                gap_simulado *= 2 # Más lento, más indetectable
            elif intensity == "alta":
                gap_simulado /= 2 # Ruidoso, exfil rápido
                
            await asyncio.sleep(gap_simulado / self.time_multiplier)
            
        logger.warning(f"[DNS TUNNELING] Completado. Total de bytes extraídos sigilosamente: {bytes_exfiltrados}")
