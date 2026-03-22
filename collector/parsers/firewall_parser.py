import os
import csv
import re
import asyncio
import hashlib
from typing import Optional
from io import StringIO

from shared.logger import get_logger
from shared.redis_bus import RedisBus

logger = get_logger("collector.parsers.firewall")

class FirewallParser:
    """
    Parsea logs de Iptables (kernel) y genérico CSV del simulador en tiempo real.
    Detecta automáticamente el formato.
    """

    def __init__(self, log_path: str, redis_bus: RedisBus):
        self.log_path = log_path
        self.redis_bus = redis_bus
        self.position_key = "parser:firewall:last_position"
        self._processed_count = 0
        self._lines_since_save = 0

        # Regex para Iptables/Kernel log
        # "Mar 20 14:32:11 kernel: [UFW BLOCK] IN=eth0 SRC=185.220.101.47 DST=192.168.1.1 PROTO=TCP DPT=22"
        self.ufw_pattern = re.compile(
            r"^(?P<timestamp>.*?) kernel:.*?\[.*? (?P<action>BLOCK|ALLOW|DROP)\].*?SRC=(?P<src_ip>[^\s]+).*?DST=(?P<dst_ip>[^\s]+).*?(?:PROTO=(?P<proto>[^\s]+))?.*?(?:DPT=(?P<dst_port>[^\s]+))?"
        )

    def _parse_csv_line(self, line: str) -> Optional[dict]:
        """Aplica lectura de CSV simulador. Headers: timestamp,action,src_ip,dst_ip,src_port,dst_port,protocol"""
        try:
            reader = csv.DictReader(StringIO(line.strip()), fieldnames=["timestamp","action","src_ip","dst_ip","src_port","dst_port","protocol"])
            row = next(reader)
            if row.get("timestamp") == "timestamp":
                return None # Ignorar header
            return {
                "timestamp": row.get("timestamp"),
                "action": row.get("action", "").upper(),
                "src_ip": row.get("src_ip"),
                "dst_ip": row.get("dst_ip"),
                "protocol": row.get("protocol"),
                "src_port": row.get("src_port"),
                "dst_port": row.get("dst_port")
            }
        except Exception:
            return None

    def _parse_ufw_line(self, line: str) -> Optional[dict]:
        """Aplica regex de UFW/Iptables."""
        match = self.ufw_pattern.search(line)
        if match:
            return {
                "timestamp": match.group("timestamp").strip(),
                "action": match.group("action").upper(),
                "src_ip": match.group("src_ip"),
                "dst_ip": match.group("dst_ip"),
                "protocol": match.group("proto"),
                "src_port": None, # Kernel raramente da source port fácil en ufw prefix
                "dst_port": match.group("dst_port")
            }
        return None

    def _parse_line(self, line: str) -> Optional[dict]:
        """Identifica el formato y delega al método correcto."""
        if not line.strip():
            return None
            
        if "kernel:" in line:
            return self._parse_ufw_line(line)
        elif "," in line:
            return self._parse_csv_line(line)
            
        return None

    async def _is_duplicate(self, h_str: str) -> bool:
        """Deduplicación por Redis hash."""
        key = f"dedup:fw:{h_str}"
        if await self.redis_bus.cache_exists(key):
            return True
        await self.redis_bus.cache_set(key, {"v":1}, ttl=600)
        return False

    async def _save_position(self, pos: int):
        try:
            await self.redis_bus.cache_set(self.position_key, {"pos": pos}, ttl=31536000)
        except Exception as e:
            logger.error(f"Fallo al guardar pos FW: {e}")

    async def _get_last_position(self) -> int:
        try:
            data = await self.redis_bus.cache_get(self.position_key)
            if data and "pos" in data:
                return data["pos"]
        except Exception as e:
            logger.error(f"Fallo al leer pos FW: {e}")
        return 0

    async def start(self) -> None:
        logger.info(f"Iniciando Firewall Parser en: {self.log_path}")
        last_pos = await self._get_last_position()
        
        while True:
            try:
                if not os.path.exists(self.log_path):
                    await asyncio.sleep(5)
                    continue

                if os.path.getsize(self.log_path) < last_pos:
                    logger.info("Rotación detectada en logs firewall.")
                    last_pos = 0

                with open(self.log_path, 'r', encoding='utf-8', errors='ignore') as f:
                    f.seek(last_pos)
                    
                    while True:
                        line = f.readline()
                        if not line:
                            if os.path.getsize(self.log_path) < f.tell():
                                last_pos = 0
                                break
                            await asyncio.sleep(0.1)
                            continue
                            
                        last_pos = f.tell()
                        
                        event_dict = self._parse_line(line)
                        if event_dict and event_dict.get("src_ip"):
                            h_str = hashlib.md5(f"{event_dict['timestamp']}-{event_dict['src_ip']}-{event_dict['dst_ip']}-{event_dict['action']}-{event_dict['dst_port']}".encode()).hexdigest()
                            
                            if not await self._is_duplicate(h_str):
                                payload = {"source": "firewall", "raw": event_dict}
                                await self.redis_bus.publish_event(self.redis_bus.STREAM_RAW, payload)
                                
                                self._processed_count += 1
                                self._lines_since_save += 1
                            
                        if self._lines_since_save >= 100:
                            await self._save_position(last_pos)
                            self._lines_since_save = 0
                            
                        if self._processed_count > 0 and self._processed_count % 1000 == 0:
                            logger.info(f"Parser Firewall procesó {self._processed_count} eventos válidos")
                            
            except Exception as e:
                logger.error(f"Error procesando tail FW: {e}")
                await asyncio.sleep(5)
