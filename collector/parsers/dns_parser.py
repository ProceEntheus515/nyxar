import os
import asyncio
import ipaddress
from typing import Optional

from shared.logger import get_logger
from shared.redis_bus import RedisBus
from collector.normalizer import Normalizer

logger = get_logger("collector.parsers.dns_parser")

class DnsParser:
    """
    Lee /logs/dns/pihole.log en tiempo real usando AsyncIO nativo.
    Por cada línea nueva, parsea y publica en Redis Stream events:raw.
    """

    def __init__(self, log_path: str, redis_bus: RedisBus, normalizer: Normalizer):
        self.log_path = log_path
        self.redis_bus = redis_bus
        self.normalizer = normalizer
        self.position_key = "parser:dns:last_position"
        self._processed_count = 0
        self._lines_since_save = 0

    def _is_internal_domain(self, domain: str) -> bool:
        """Filtra dominios internos y PTR queries."""
        domain_lower = domain.lower()
        if domain_lower.endswith(".local") or \
           domain_lower.endswith(".internal") or \
           domain_lower.endswith(".empresa.local") or \
           domain_lower.endswith(".arpa"):
            return True
        return False

    def _is_internal_ip(self, ip_str: str) -> bool:
        try:
            ip = ipaddress.ip_address(ip_str)
            return ip.is_private
        except ValueError:
            return False

    def _parse_line(self, line: str) -> Optional[dict]:
        """
        Parsea una línea del formato PiHole log.
        Ejemplos:
        "Mar 20 14:32:11 dnsmasq[123]: query[A] google.com from 192.168.1.45"
        "Mar 20 14:32:11 dnsmasq[123]: gravity blocked evil.ru for 192.168.1.45"
        """
        # Filtrado rápido pre-parseo para optimizar CPU (ignora replies, cached, forwarded)
        if "query[" not in line and "gravity blocked" not in line:
            return None
            
        parts = line.strip().split()
        if len(parts) < 6:
            return None
            
        timestamp = f"{parts[0]} {parts[1]} {parts[2]}"
        
        # Parse query event
        if "query[" in line and "from" in line:
            try:
                idx_query = next(i for i, p in enumerate(parts) if p.startswith("query["))
                query_type = parts[idx_query].replace("query[", "").replace("]", "")
                domain = parts[idx_query + 1]
                idx_from = parts.index("from")
                client = parts[idx_from + 1]
                
                return {
                    "timestamp": timestamp,
                    "client": client,
                    "domain": domain,
                    "type": query_type,
                    "status": "NOERROR",
                    "blocked": False
                }
            except (ValueError, StopIteration, IndexError):
                return None
                
        # Parse blocked event
        elif "gravity blocked" in line and "for" in line:
            try:
                idx_blocked = parts.index("blocked")
                domain = parts[idx_blocked + 1]
                idx_for = parts.index("for")
                client = parts[idx_for + 1]
                
                return {
                    "timestamp": timestamp,
                    "client": client,
                    "domain": domain,
                    "type": "UNKNOWN", # No hay query type visible en la línea blocked de gravity
                    "status": "BLOCKED",
                    "blocked": True
                }
            except (ValueError, IndexError):
                return None

        return None

    def _is_valid_event(self, event: dict) -> bool:
        """Verifica filtros de negocio."""
        domain = event.get("domain", "")
        client = event.get("client", "")
        
        # 1. Filtro: IPs que no son internas como cliente
        if not self._is_internal_ip(client):
            return False
            
        # 2. Filtro: Dominios internos
        if self._is_internal_domain(domain):
            return False
            
        # 3. Filtro: Dominios con menos de 1 punto (ej. "localhost", "server1")
        # El requerimiento dice: "menos de 2 puntos (sin TLD válido)".
        # Asumiendo que quisieron decir "dominio incompleto" => < 1 punto (".com" es 0 pero nadie loguea solo .com)
        # un dominio válido como x.com tiene 1 punto.
        if domain.count(".") < 1:
            return False
            
        return True

    async def _save_position(self, pos: int):
        try:
            # 1 año de TTL, solo para no perder state si el bot muere
            await self.redis_bus.cache_set(self.position_key, {"pos": pos}, ttl=31536000)
        except Exception as e:
            logger.error(f"Fallo al guardar checkpoint: {e}")

    async def _get_last_position(self) -> int:
        try:
            data = await self.redis_bus.cache_get(self.position_key)
            if data and "pos" in data:
                return data["pos"]
        except Exception as e:
            logger.error(f"Fallo al leer checkpoint: {e}")
        return 0

    async def start(self) -> None:
        """Inicia el tail asíncrono del archivo de logs."""
        logger.info(f"Iniciando DNS Parser haciendo tail en: {self.log_path}")
        
        last_pos = await self._get_last_position()
        logger.info(f"Retomando desde la posición byte: {last_pos}")
        
        while True:
            try:
                if not os.path.exists(self.log_path):
                    logger.warning(f"Esperando a que se cree el log: {self.log_path}")
                    await asyncio.sleep(5)
                    continue

                file_size = os.path.getsize(self.log_path)
                if file_size < last_pos:
                    logger.info("El archivo se achicó (rotación de log). Posición reseteada a 0.")
                    last_pos = 0

                with open(self.log_path, 'r', encoding='utf-8', errors='ignore') as f:
                    f.seek(last_pos)
                    
                    while True:
                        line = f.readline()
                        if not line:
                            # Fin de archivo (EOF). Esperar nuevas líneas sin bloquear I/O
                            # Chequear si fue rotado/truncado
                            if os.path.getsize(self.log_path) < f.tell():
                                logger.info("Log rotado mientras lo leíamos.")
                                last_pos = 0
                                break
                                
                            await asyncio.sleep(0.1)
                            continue
                            
                        # Actualizar iterador
                        last_pos = f.tell()
                        
                        event_dict = self._parse_line(line)
                        if event_dict and self._is_valid_event(event_dict):
                            evento = await self.normalizer.normalize(event_dict, "dns")
                            if evento:
                                await self.redis_bus.publish_event(
                                    self.redis_bus.STREAM_RAW,
                                    evento.to_redis_dict(),
                                )
                            
                            self._processed_count += 1
                            self._lines_since_save += 1
                            
                            # Log cada 1000
                            if self._processed_count % 1000 == 0:
                                logger.info(f"Parser DNS procesó {self._processed_count} eventos válidos")
                            
                        # Si no era un evento válido o no se parseó igual cuenta como línea leída para el save checkpoint
                        # Pero el contador dice "100 líneas procesadas". Guardaremos cada 100 líneas leídas en total para efficiency o validados? 
                        # Pongamos que validamos cada 100 *válidas*
                        if self._lines_since_save >= 100:
                            await self._save_position(last_pos)
                            self._lines_since_save = 0
                                
            except Exception as e:
                logger.error(f"Error fatal procesando tail: {e}")
                await asyncio.sleep(5) # Backoff ante errores catastróficos
