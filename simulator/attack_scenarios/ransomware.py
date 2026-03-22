import random
import string
import asyncio
from typing import Literal
from datetime import datetime

from shared.logger import get_logger
from .base import BaseAttackScenario

logger = get_logger("scenario.ransomware")

class RansomwareScenario(BaseAttackScenario):

    @property
    def description(self) -> str:
        return "Simula infección progresiva de ransomware: beaconing, escaneo lateral, exfiltración masiva (cifrado extrínseco) y salto sobre honeypot de directorios."

    def _generate_dga(self) -> str:
        """Genera dominio DGA pseudoaleatorio para C2"""
        length = random.randint(12, 20)
        chars = random.choices(string.ascii_lowercase + string.digits, k=length)
        tlds = ["com", "xyz", "ru", "net"]
        return f"{''.join(chars)}.{random.choice(tlds)}"

    async def execute(self, intensity: Literal["baja", "media", "alta"]) -> None:
        logger.info(f"[RANSOMWARE] Iniciando ataque en dispositivo {self.target['dispositivo']}. Fase inicial (Beaconing).")
        
        # Tiempos (ajustados a Lab Mode o real)
        # 5 minutos simulados beaconing:
        beacon_interval_real = (5 * 60) / self.time_multiplier
        # Dominios cambian cada 6 horas (360 mins) => 6 * 60 * 60 / multi
        domain_rotation_real = (6 * 60 * 60) / self.time_multiplier
        
        current_c2 = self._generate_dga()
        logger.info(f"[RANSOMWARE] C2 Activo inicial: {current_c2}")

        # Fase 1: Beaconing en la corrutina concurrente
        async def beacon_loop():
            nonlocal current_c2
            last_rotation = asyncio.get_event_loop().time()
            while True:
                now = datetime.now()
                # Rotar DGA?
                if asyncio.get_event_loop().time() - last_rotation > domain_rotation_real:
                    current_c2 = self._generate_dga()
                    logger.info(f"[RANSOMWARE] Rotando C2 DGA -> {current_c2}")
                    last_rotation = asyncio.get_event_loop().time()
                
                dns_event = {
                    "timestamp": now.strftime("%b %d %H:%M:%S"),
                    "client": self.target["dispositivo"],
                    "domain": current_c2,
                    "type": "A",
                    "status": "NOERROR",
                    "blocked": False
                }
                await self.redis_bus.publish_event(self.redis_bus.STREAM_RAW, {"source": "dns", "raw": dns_event})
                
                # Proxy payload para el ping home
                proxy_event = {
                    "timestamp": f"{now.timestamp():.3f}",
                    "client_ip": self.target["dispositivo"],
                    "method": "POST",
                    "url": f"https://{current_c2}/api/v1/ping",
                    "status_code": "200",
                    "bytes": str(random.randint(150, 400)), # Muy chicos, heartbeats
                    "destination_ip": f"{random.randint(1,255)}.120.50.4"
                }
                await self.redis_bus.publish_event(self.redis_bus.STREAM_RAW, {"source": "proxy", "raw": proxy_event})
                
                await asyncio.sleep(beacon_interval_real)
                
        # Lanzar beaconing independiente
        beacon_task = asyncio.create_task(beacon_loop())
        
        try:
            if intensity == "baja":
                # Solo beaconing para tests pasivos continuos
                await asyncio.sleep(86400) # Dejarlo 1 día zombie
                return

            # MEDIA o ALTA pasan a Fase 2: Exploración lateral (+2 hs simuladas)
            delay_exploration_real = (2 * 60 * 60) / self.time_multiplier
            logger.info(f"[RANSOMWARE] Esperando {delay_exploration_real:.1f}s reales para iniciar Exploración Lateral...")
            await asyncio.sleep(delay_exploration_real)
            
            logger.info(f"[RANSOMWARE] Fase 2 activa: Escaneando red local desde {self.target['dispositivo']}")
            subnet = ".".join(self.target["dispositivo"].split(".")[:3])
            # Disparar fw conexiones a ips del /24 que no son las habituales
            for i in range(1, 20): 
                fake_victim = f"{subnet}.{random.randint(50,250)}"
                fw_event = {
                    "timestamp": datetime.now().strftime("%b %d %H:%M:%S"),
                    "action": "BLOCK" if random.random() < 0.8 else "ALLOW",
                    "src_ip": self.target["dispositivo"],
                    "dst_ip": fake_victim,
                    "src_port": str(random.randint(20000, 60000)),
                    "dst_port": random.choice(["445", "139", "3389"]),
                    "protocol": "TCP"
                }
                await self.redis_bus.publish_event(self.redis_bus.STREAM_RAW, {"source": "firewall", "raw": fw_event})
                await asyncio.sleep(0.5 / self.time_multiplier)

            if intensity == "media":
                await asyncio.sleep(86400)
                return

            # ALTA pasa a Fase 3 y 4: Exfiltración masiva de Día 1 (simulado a 24h tras inicio)
            delay_activation_real = (22 * 60 * 60) / self.time_multiplier
            logger.info(f"[RANSOMWARE] Esperando {delay_activation_real:.1f}s reales hasta activación y exfiltración de Día 1.")
            await asyncio.sleep(delay_activation_real)
            
            logger.critical(f"[RANSOMWARE] Fase ALTA actívada. Cifrando y exfiltrando asíncronamente desde {self.target['dispositivo']}")
            
            # 10x volumen hacia dominios turbios
            for i in range(15):
                now = datetime.now()
                proxy_event = {
                    "timestamp": f"{now.timestamp():.3f}",
                    "client_ip": self.target["dispositivo"],
                    "method": "POST",
                    "url": "http://transfer-huge-drop.ru/upload",
                    "status_code": "200",
                    "bytes": f"{random.randint(50, 200) * 1024 * 1024}", # 50-200 GB
                    "destination_ip": "185.10.15.5"
                }
                await self.redis_bus.publish_event(self.redis_bus.STREAM_RAW, {"source": "proxy", "raw": proxy_event})
                await asyncio.sleep(30 / self.time_multiplier)
                
            # Honeypot final Hit
            logger.error("[RANSOMWARE] Ransomware detectó un SMB Share protegido. Pisando trampilla honeypot.")
            fw_event = {
                "timestamp": datetime.now().strftime("%b %d %H:%M:%S"),
                "action": "ALLOW",
                "src_ip": self.target["dispositivo"],
                "dst_ip": "192.168.1.99", # Asumimos ip honeypot para logs
                "src_port": "45091",
                "dst_port": "445",
                "protocol": "TCP",
                "honeypot_share": "\\\\fileserver01\\BACKUP_FINANCIERO_2025"
            }
            # Agregamos evento especializado
            # Para esto el collector/correlator podría recibir logs enriquecidos de un fw.
            # Según prompt: (genera un evento especial de tipo honeypot_hit). Lo tiramos directo al bus o vía webhook falso
            await self.redis_bus.publish_event(self.redis_bus.STREAM_RAW, {"source": "wazuh", "raw": {
                "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%S.000+0000"),
                "agent": {"ip": self.target["dispositivo"], "name": self.target["hostname"]},
                "rule": {
                    "level": 14,
                    "description": f"Ransomware honeypot trigger: attempt to access \\\\fileserver01\\BACKUP_FINANCIERO_2025",
                    "groups": ["ransomware", "honeypot"],
                    "id": "100001"
                }
            }})
            
            logger.critical("[RANSOMWARE] Secuencia finalizada. Máquina comprometida totalmente.")
            
        finally:
            beacon_task.cancel()
