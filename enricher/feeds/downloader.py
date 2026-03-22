import os
import re
import json
import asyncio
import httpx
import ipaddress
from datetime import datetime
from typing import Optional, List, Set

from shared.logger import get_logger
from shared.redis_bus import RedisBus

logger = get_logger("enricher.feeds.downloader")

class FeedDownloader:
    
    FEEDS = {
        "spamhaus_drop": {
            "url": "https://www.spamhaus.org/drop/drop.txt",
            "tipo": "cidr",
            "redis_key": "blocklist:spamhaus_drop"
        },
        "spamhaus_edrop": {
            "url": "https://www.spamhaus.org/drop/edrop.txt", 
            "tipo": "cidr",
            "redis_key": "blocklist:spamhaus_edrop"
        },
        "feodo_ip": {
            "url": "https://feodotracker.abuse.ch/downloads/ipblocklist.txt",
            "tipo": "ip",
            "redis_key": "blocklist:feodo"
        },
        "urlhaus_domains": {
            "url": "https://urlhaus.abuse.ch/downloads/text/",
            "tipo": "dominio",
            "redis_key": "blocklist:urlhaus"
        },
        "threatfox_iocs": {
            "url": "https://threatfox.abuse.ch/export/json/recent/",
            "tipo": "json",
            "redis_key": "blocklist:threatfox"
        }
    }
    
    def __init__(self, redis_bus: RedisBus):
        self.redis_bus = redis_bus
        self._cached_cidrs = {}

    async def start_scheduler(self) -> None:
        """Loop infinito de actualización horaria."""
        logger.info("[DOWNLOADER] Inicializando el Feed Downloader Task")
        while True:
            await self.download_all()
            logger.info("[DOWNLOADER] Durmiendo por 3600 segundos hasta próximo cron")
            await asyncio.sleep(3600)

    async def download_all(self) -> None:
        """Descarga concurrente garantizada sin bloqueos."""
        logger.info("[DOWNLOADER] Disparando gather() concurrente para actualización de feeds crudos.")
        
        # Inyecta paralelismo masivo
        tasks = []
        for nombre, conf in self.FEEDS.items():
            tasks.append(asyncio.create_task(self.download_feed(nombre, conf)))
            
        await asyncio.gather(*tasks, return_exceptions=True)

    async def download_feed(self, nombre: str, config: dict) -> None:
        """
        Streamed parsing para no reventar la memoria.
        Guarda en el Redis (SADD masivo) el listado actualizado.
        """
        redis_client = self.redis_bus.client
        if not redis_client:
            logger.error("[DOWNLOADER] No hay cliente redis vivo")
            return
            
        url = config["url"]
        tipo = config["tipo"]
        redis_key = config["redis_key"]
        tmp_key = f"{redis_key}:tmp" # Usar una key volátil para un hot-swap seguro
        
        added_count = 0
        
        timeout = httpx.Timeout(30.0)
        
        try:
            logger.info(f"[{nombre}] Iniciando stream fetch desde {url}")
            async with httpx.AsyncClient(timeout=timeout) as client:
                async with client.stream('GET', url) as r:
                    r.raise_for_status()
                    
                    # Borramos el tmp por si quedó basureado anteriomente
                    await redis_client.delete(tmp_key)
                    
                    buffer_size = 500
                    pipe = redis_client.pipeline()
                    
                    # Para tipo json, usaremos un extractor de regEx línea a línea por IOC 
                    # para saltar el límite de tamaño sin usar json.loads(full_string)
                    # Threatfox usa "ioc_value": "..."
                    ioc_pattern = re.compile(r'"ioc_value"\:\s*"([^"]+)"')
                    
                    async for line in r.aiter_lines():
                        clean_line = line.strip()
                        if not clean_line or clean_line.startswith("#"):
                            continue
                            
                        extracted_value = None
                        
                        if tipo == "json":
                            match = ioc_pattern.search(clean_line)
                            if match:
                                val = match.group(1).split(":")[0] # Threatfox a veces manda IP:Port
                                if "://" in val: # O URLs enteras
                                    val = val.split("://")[-1].split("/")[0] # Solo el dominio
                                extracted_value = val
                        elif tipo == "cidr":
                            extracted_value = clean_line.split(";")[0].strip().split()[0] # Evitar comentarios al lado del CIDR si lo hay
                        else:  # ip o dominio text plains
                            extracted_value = clean_line
                            
                        if extracted_value:
                            pipe.sadd(tmp_key, extracted_value)
                            added_count += 1
                            
                            if added_count % buffer_size == 0:
                                await pipe.execute()
                                
                    await pipe.execute() # Flush restante
                    
            if added_count > 0:
                # Hot-Swap Renaming (O(1)) garantiza no interrupción y zero down-time
                await redis_client.rename(tmp_key, redis_key)
                
                # Timestamp persistente
                ts = datetime.now().isoformat()
                await redis_client.set(f"{redis_key}:updated", ts)
                
                # Cache local flushing para CIDRs
                if tipo == "cidr" and redis_key in self._cached_cidrs:
                    del self._cached_cidrs[redis_key]
                    
                logger.info(f"[{nombre}] Finalizado. ¡IOCs inyectados: {added_count}!")
            else:
                logger.warning(f"[{nombre}] Feed descargado sin datos nuevos. Abortando update.")
                await redis_client.delete(tmp_key)
                
        except Exception as e:
            logger.error(f"[{nombre}] Falla descargando listado: {e} | Usando reliquias previas.")

    async def _get_cidr_set(self, key: str) -> List[Any]:
        """Recupera la lista cruda CIDR desde Redis y la transforma en local cached ip_networks objectos."""
        if key in self._cached_cidrs:
            return self._cached_cidrs[key]
            
        r = self.redis_bus.client
        if r:
            raw_cidrs = await r.smembers(key)
            networks = []
            for raw in raw_cidrs:
                try:
                    c = raw.decode() if isinstance(raw, bytes) else str(raw)
                    networks.append(ipaddress.ip_network(c))
                except Exception:
                    continue
            self._cached_cidrs[key] = networks
            return networks
        return []

    async def check_ip(self, ip: str) -> Optional[str]:
        """
        Revisa IPs y CIDR blocks. Retorna la list.
        """
        r = self.redis_bus.client
        if not r: return None
        
        try:
            target = ipaddress.ip_address(ip)
        except ValueError:
            return None # Inválida
            
        # Revisión SET directo puro O(1)
        if await r.sismember("blocklist:feodo", ip): return "feodo_ip"
        if await r.sismember("blocklist:threatfox", ip): return "threatfox_iocs"
        
        # Revisión CIDR O(N) cacheado
        for cidr_list in [self.FEEDS["spamhaus_drop"]["redis_key"], self.FEEDS["spamhaus_edrop"]["redis_key"]]:
            redes = await self._get_cidr_set(cidr_list)
            if any(target in network for network in redes):
                return cidr_list.replace("blocklist:", "")

        return None

    async def check_domain(self, domain: str) -> Optional[str]:
        """
        Chequeo de sufijos y dominios FQDN 
        sub.evil.com => eval eval.com
        """
        domain = domain.lower()
        r = self.redis_bus.client
        if not r: return None
        
        parts = domain.split(".")
        permutations = []
        for i in range(len(parts)-1):
            permutations.append(".".join(parts[i:]))
        
        pipe = r.pipeline()
        for p in permutations:
            pipe.sismember("blocklist:urlhaus", p)
            pipe.sismember("blocklist:threatfox", p)
            
        resultados = await pipe.execute()
        
        # Recorremos la pipeline de a pares {urlhaus, threatfox}
        for idx, perm in enumerate(permutations):
            is_urlhaus = resultados[idx*2]
            is_threatfox = resultados[idx*2 + 1]
            if is_urlhaus: return "urlhaus_domains"
            if is_threatfox: return "threatfox_iocs"
            
        return None

    async def get_stats(self) -> dict:
        r = self.redis_bus.client
        stats_map = {}
        if not r: return stats_map
        
        for k in self.FEEDS.keys():
            rkey = self.FEEDS[k]["redis_key"]
            try:
                cardinalidad = await r.scard(rkey)
                update_ts = await r.get(f"{rkey}:updated")
                if update_ts: update_ts = update_ts.decode("utf-8") if isinstance(update_ts, bytes) else str(update_ts)
                
                stats_map[k] = {
                    "count": cardinalidad,
                    "last_updated": update_ts or "Never"
                }
            except Exception:
                pass
        return stats_map
