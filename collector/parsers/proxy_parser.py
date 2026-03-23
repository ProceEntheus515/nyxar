import os
import asyncio
import hashlib
from typing import Optional
from urllib.parse import urlparse

from shared.logger import get_logger
from shared.redis_bus import RedisBus
from collector.normalizer import Normalizer

logger = get_logger("collector.parsers.proxy")

class ProxyParser:
    """
    Parsea logs de Squid proxy en tiempo real.
    Formato esperado (Combined modificiado/Squid nativo adaptado):
    timestamp elapsed client action/status bytes method url user hierarchy/ip content_type
    """

    def __init__(self, log_path: str, redis_bus: RedisBus, normalizer: Normalizer):
        self.log_path = log_path
        self.redis_bus = redis_bus
        self.normalizer = normalizer
        self.position_key = "parser:proxy:last_position"
        self._processed_count = 0
        self._lines_since_save = 0

    def _is_valid_event(self, event: dict) -> bool:
        """Verifica filtros de negocio."""
        status = event.get("status_code", "")
        # Filtrar status_code 0
        if status == "0" or status == 0:
            return False
            
        method = str(event.get("method", "")).upper()
        url = str(event.get("url", ""))
        
        # Filtrar métodos CONNECT a puertos diferentes a 443
        if method == "CONNECT":
            parsed = urlparse(f"http://{url}") if not url.startswith("http") else urlparse(url)
            port = parsed.port
            if port and port != 443:
                return False

        return True

    def _parse_line(self, line: str) -> Optional[dict]:
        """
        Extrae datos de Squid Log.
        Ej: "1711020731.000  42 192.168.1.45 TCP_MISS/200 8523 GET http://example.com/ - DIRECT/93.184.216.34 text/html"
        """
        parts = line.strip().split()
        if len(parts) < 10:
            return None
            
        try:
            timestamp = parts[0]
            client_ip = parts[2]
            action_status = parts[3]
            status_code = action_status.split("/")[1] if "/" in action_status else "UNKNOWN"
            bytes_sent = parts[4]
            method = parts[5].upper()
            url = parts[6]
            hierarchy_ip = parts[8]
            destination_ip = hierarchy_ip.split("/")[1] if "/" in hierarchy_ip else ""
            
            return {
                "timestamp": timestamp,
                "client_ip": client_ip,
                "method": method,
                "url": url,
                "status_code": status_code,
                "bytes": bytes_sent,
                "destination_ip": destination_ip
            }
        except (IndexError, ValueError) as e:
            logger.debug(f"Error parseando proxy log: {e}")
            return None

    async def _is_duplicate(self, content_hash: str) -> bool:
        """Previene procesar el mismo evento usando un hash en Redis."""
        key = f"dedup:proxy:{content_hash}"
        
        if await self.redis_bus.cache_exists(key):
            return True
            
        # TTL 10 minutos (600s) ventana deduplicacion
        await self.redis_bus.cache_set(key, {"v": 1}, ttl=600)
        return False

    async def _save_position(self, pos: int):
        try:
            await self.redis_bus.cache_set(self.position_key, {"pos": pos}, ttl=31536000)
        except Exception as e:
            logger.error(f"Fallo al guardar pos Proxy: {e}")

    async def _get_last_position(self) -> int:
        try:
            data = await self.redis_bus.cache_get(self.position_key)
            if data and "pos" in data:
                return data["pos"]
        except Exception as e:
            logger.error(f"Fallo al leer pos Proxy: {e}")
        return 0

    async def start(self) -> None:
        logger.info(f"Iniciando Proxy Parser en: {self.log_path}")
        last_pos = await self._get_last_position()
        
        while True:
            try:
                if not os.path.exists(self.log_path):
                    await asyncio.sleep(5)
                    continue

                if os.path.getsize(self.log_path) < last_pos:
                    logger.info("Rotación detectada en logs proxy.")
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
                        if event_dict and self._is_valid_event(event_dict):
                            raw_str = f"{event_dict['timestamp']}-{event_dict['client_ip']}-{event_dict['url']}-{event_dict['bytes']}"
                            h = hashlib.md5(raw_str.encode()).hexdigest()
                            
                            if not await self._is_duplicate(h):
                                evento = await self.normalizer.normalize(event_dict, "proxy")
                                if evento:
                                    await self.redis_bus.publish_event(
                                        self.redis_bus.STREAM_RAW,
                                        evento.to_redis_dict(),
                                    )
                                
                                self._processed_count += 1
                                self._lines_since_save += 1
                            
                        if self._lines_since_save >= 100:
                            await self._save_position(last_pos)
                            self._lines_since_save = 0
                            
                        if self._processed_count > 0 and self._processed_count % 1000 == 0:
                            logger.info(f"Parser Proxy procesó {self._processed_count} eventos válidos")
                            
            except Exception as e:
                logger.error(f"Error procesando tail Proxy: {e}")
                await asyncio.sleep(5)
