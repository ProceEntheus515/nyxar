import asyncio
from typing import Optional

from shared.redis_bus import RedisBus
from api.models import Enrichment

class EnrichmentCache:
    """Capacidades de cacheo específicas usando RedisBus como backend."""
    
    def __init__(self, redis_bus: RedisBus):
        self.redis_bus = redis_bus
        self.hit_key = "enricher:stats:hits"
        self.miss_key = "enricher:stats:misses"
        
    async def get_enrichment(self, valor: str) -> Optional[Enrichment]:
        key = f"enrich:{valor}"
        data = await self.redis_bus.cache_get(key)
        if data:
            try:
                # Validamos y transformamos al modelo
                return Enrichment(**data)
            except Exception:
                return None
        return None
        
    async def set_enrichment(self, valor: str, enrichment: Enrichment, ttl_seconds: int = 86400) -> None:
        key = f"enrich:{valor}"
        await self.redis_bus.cache_set(key, enrichment.model_dump(), ttl=ttl_seconds)
        
    async def record_hit(self) -> None:
        """Incrementa el contador estadístico de hit (usando el bus asíncrono subyacente de pubsub/redis)."""
        # Ya que redis_bus no tiene incr, le enviamos comando crudo al client
        try:
            r = self.redis_bus.client
            if r:
                await r.incr(self.hit_key)
        except Exception:
            pass
            
    async def record_miss(self) -> None:
        try:
            r = self.redis_bus.client
            if r:
                await r.incr(self.miss_key)
        except Exception:
            pass
            
    async def get_stats(self) -> dict:
        try:
            r = self.redis_bus.client
            if not r:
                return {}
                
            hits = int(await r.get(self.hit_key) or 0)
            misses = int(await r.get(self.miss_key) or 0)
            
            # Patrón scan rudimentario para ver keys
            # Usualmente en prod usaríamos SCARD o DBSIZE, aquí aproximamos o trackeamos manual
            cursor = b"0"
            total_keys = 0
            while cursor:
                cursor, keys = await r.scan(cursor=cursor, match="enrich:*", count=5000)
                total_keys += len(keys)
                if cursor == b"0":
                    break
                    
            total_calls = hits + misses
            hit_rate = (hits / total_calls * 100) if total_calls > 0 else 0.0
            
            return {
                "total_keys": total_keys,
                "hits": hits,
                "misses": misses,
                "hit_rate_pct": round(hit_rate, 2)
            }
        except Exception:
            return {"total_keys": 0, "hit_rate_pct": 0.0}
