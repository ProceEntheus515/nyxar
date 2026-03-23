import asyncio
import random
from typing import Literal
from datetime import datetime

from shared.logger import get_logger
from .base import BaseAttackScenario

logger = get_logger("scenario.lateral_movement")

class LateralMovementScenario(BaseAttackScenario):

    @property
    def description(self) -> str:
        return "Simula pivoteo y escaneo horizontal de puertos desde el host comprometido."

    async def execute(self, intensity: Literal["baja", "media", "alta"]) -> None:
        logger.warning(f"[LATERAL MOVEMENT] Iniciando barrido activo desde la IP {self.target['dispositivo']}")
        
        # Segmento /24 de la IP target
        octets = self.target["dispositivo"].split(".")
        subnet = f"{octets[0]}.{octets[1]}.{octets[2]}"
        misma_ip = int(octets[3])
        
        puertos_comunes = ["22", "445", "3389", "5985"]
        
        # Mezclamos target IPs locales a recorrer para simular port scanning secuencial
        ips_a_escanear = [i for i in range(1, 255) if i != misma_ip and i != 10] # Evitamos colisión con 192.168.1.10 si fuese nuestro target
        random.shuffle(ips_a_escanear)
        
        # Para acelerar la simulación o modularla según "intensity" solo agarramos una cuota
        if intensity == "baja":
            ips_a_escanear = ips_a_escanear[:50]
        elif intensity == "media":
            ips_a_escanear = ips_a_escanear[:120]
            
        exitosos = random.sample(ips_a_escanear, k=random.randint(2, 3)) # Algunos lograrán ALLOW
            
        logger.info(f"[LATERAL MOVEMENT] Total de targets a sondear: {len(ips_a_escanear)}. Expected ALLOWS: {len(exitosos)}")
        
        for ip in ips_a_escanear:
            target_ip = f"{subnet}.{ip}"
            now = datetime.now()
            
            for puerto in puertos_comunes:
                # Decidimos ALLOW block
                action = "ALLOW" if ip in exitosos and random.random() < 0.3 else "BLOCK"
                
                fw_event = {
                    "timestamp": now.strftime("%b %d %H:%M:%S"),
                    "action": action,
                    "src_ip": self.target["dispositivo"],
                    "dst_ip": target_ip,
                    "src_port": str(random.randint(49152, 65535)),
                    "dst_port": puerto,
                    "protocol": "TCP"
                }
                
                await self._publish_normalized(fw_event, "firewall")
                
                # Frecuencia: escaneo horizontal (1 intento c/ 2-5 segundos)
                # Escalar x tiempo
                gap_simulado = random.uniform(2, 5)
                await asyncio.sleep(gap_simulado / self.time_multiplier)

        # Finalmente: conexión exitosa a DC
        logger.critical(f"[LATERAL MOVEMENT] Escaneo masivo culminado. Explotando credenciales vulnerables contra DC...")
        # DC IP simulada (asumimos .100 si no es conocida, pero mejor usar fqdn/resolución o usar la metadata `dc01.local`)
        # Enviamos fw de ALLOW + WAZUH pass alert
        dc_ip = f"{subnet}.10" # Typical DC ip en lab
        fw_dc_event = {
            "timestamp": datetime.now().strftime("%b %d %H:%M:%S"),
            "action": "ALLOW",
            "src_ip": self.target["dispositivo"],
            "dst_ip": dc_ip,
            "src_port": "56980",
            "dst_port": "5985", # WinRM
            "protocol": "TCP"
        }
        await self._publish_normalized(fw_dc_event, "firewall")
        
        # Si lograron acceso al DC => alerta Wazuh critica 
        wz_event = {
            "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%S.000+0000"),
            "agent": {"ip": dc_ip, "name": "dc01"},
            "rule": {
                "level": 12, # Windows logon success anomalo
                "description": f"Suspect remote Powershell Execution (WinRM) from {self.target['dispositivo']} to Domain Controller",
                "groups": ["windows", "recon"],
                "id": "60111"
            }
        }
        await self._publish_normalized(wz_event, "wazuh")
        logger.error(f"[LATERAL MOVEMENT] Finalizado. El host {self.target['dispositivo']} tiene sesión PSSession viva en dc01.local")
