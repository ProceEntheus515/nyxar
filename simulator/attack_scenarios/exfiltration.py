import asyncio
import random
from typing import Literal
from datetime import datetime

from shared.logger import get_logger
from .base import BaseAttackScenario

logger = get_logger("scenario.exfiltration")

class ExfiltrationScenario(BaseAttackScenario):

    @property
    def description(self) -> str:
        return "Simula filtración nocturna masiva de datos (mega/drive) mediante User-Agents no estandarizados."

    async def execute(self, intensity: Literal["baja", "media", "alta"]) -> None:
        logger.critical(f"[EXFILTRATION] Comenzando subida masiva de archivos protegidos en {self.target['dispositivo']}")
        
        # Baseline del usuario en MB (para hacer 5-10x)
        baseline = self.target.get("volumen_mb_dia", 100)
        multiplicador = random.uniform(5, 10) # 5-10x
        if intensity == "baja":
            multiplicador = 3
        elif intensity == "alta":
            multiplicador = 15
            
        mb_objetivo = baseline * multiplicador
        logger.info(f"[EXFILTRATION] Baseline dictaba: {baseline}MB. Inyectaré {mb_objetivo:.0f}MB hacia la nube.")

        dominios_nube = ["mega.nz", "drive.google.com", "dropbox.com", "wetransfer.com", "onedrive.live.com"]
        destino_nube = random.choice(dominios_nube)
        
        # Duracion 45-90 min
        mins_duracion = random.randint(45, 90)
        logger.info(f"[EXFILTRATION] Subida distribuida en chunk proxies a través de {mins_duracion} mins simulados.")
        
        chunks = int(mins_duracion / 2) # aprox 1 petición extra pesada cada 2 min (para simular uploads continuos multihilo o parts grandotas)
        bytes_por_chunk = int((mb_objetivo * 1024 * 1024) / chunks)

        user_agent_anomalo = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) curl/7.88.1"

        for idx in range(chunks):
            now = datetime.now()
            # Timestamp irreal fuera de rango si estuviesemos fijando hora
            # Como corre asíncronamente con real datetime y queremos 2 AM
            # Solo podemos emitirlo "ahora mismo" y el trigger lo activará el simulador de cron.
            # *Nota*: para fines de logs asume el "ahora" emitido en este tick como fuera de hora si un orquestador cron lo corre de madrugada.
            
            # DNS previo (solo el primero o alguno random)
            if idx == 0 or random.random() < 0.1:
                dns_event = {
                    "timestamp": now.strftime("%b %d %H:%M:%S"),
                    "client": self.target["dispositivo"],
                    "domain": destino_nube,
                    "type": "A",
                    "status": "NOERROR",
                    "blocked": False
                }
                await self._publish_normalized(dns_event, "dns")
                
            proxy_event = {
                "timestamp": f"{now.timestamp():.3f}",
                "client_ip": self.target["dispositivo"],
                "method": "POST",
                "url": f"https://{destino_nube}/api/v1/upload-chunk-{idx}",
                "status_code": "200",
                "bytes": str(bytes_por_chunk),
                "destination_ip": "104.22.4.19", # Genérico para mega
                "user_agent": user_agent_anomalo
            }
            await self._publish_normalized(proxy_event, "proxy")
            
            gap_simulado = (mins_duracion * 60) / chunks
            await asyncio.sleep(gap_simulado / self.time_multiplier)
            
        logger.error(f"[EXFILTRATION] Culminado. Se extrajeron {mb_objetivo:.0f}MB hacia {destino_nube}")
