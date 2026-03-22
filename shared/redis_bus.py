import os
import json
import time
import uuid
import asyncio
import redis.asyncio as redis
from typing import Optional, List, Callable, Any, Tuple
from shared.logger import get_logger

logger = get_logger("redis_bus")

class RedisBus:
    STREAM_RAW = "events:raw"
    STREAM_ENRICHED = "events:enriched"
    STREAM_ALERTS = "events:alerts"
    CACHE_PREFIX_ENRICH = "enrich:"
    CACHE_PREFIX_BASELINE = "baseline:"
    CACHE_TTL_ENRICH = 86400       # 24 horas
    CACHE_TTL_BASELINE = 3600      # 1 hora
    MISP_HITS_ZSET = "misp:hits"

    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        self.pool: Optional[redis.ConnectionPool] = None
        self.client: Optional[redis.Redis] = None

    async def _retry_operation(self, operation: Callable, *args, **kwargs) -> Any:
        """Helper para ejecutar operaciones Redis con 3 reintentos y backoff exponencial."""
        attempts = 3
        for attempt in range(attempts):
            try:
                if not self.client:
                    await self.connect()
                return await operation(*args, **kwargs)
            except (redis.ConnectionError, redis.TimeoutError) as e:
                logger.error(f"Error de conexión Redis (Intento {attempt+1}/{attempts}): {e}")
                if attempt == attempts - 1:
                    raise
                await asyncio.sleep(2 ** attempt)  # Backoff: 1s, 2s
            except Exception as e:
                logger.error(f"Error inesperado procesando operación Redis: {e}")
                raise

    async def connect(self) -> None:
        if not self.pool:
            logger.info("Iniciando pool de conexiones Redis", extra={"url": self.redis_url})
            self.pool = redis.ConnectionPool.from_url(
                self.redis_url, 
                max_connections=20, 
                decode_responses=True
            )
            self.client = redis.Redis(connection_pool=self.pool)

    async def disconnect(self) -> None:
        if self.pool:
            logger.info("Cerrando pool de conexiones Redis")
            await self.pool.disconnect()
            self.pool = None
            self.client = None

    # --- STREAMS ---

    async def publish_event(self, stream: str, evento: dict) -> str:
        async def op():
            return await self.client.xadd(stream, {"data": json.dumps(evento)}, maxlen=10000)
        return await self._retry_operation(op)

    async def consume_events(self, stream: str, group: str, consumer: str, count: int = 10) -> List[Tuple[str, dict]]:
        async def op():
            try:
                # Crea el Consumer Group, mkstream=True crea el stream si no existe
                await self.client.xgroup_create(stream, group, mkstream=True)
            except redis.ResponseError as e:
                if "BUSYGROUP" not in str(e):
                    raise
            
            # '>' significa mensajes nunca leidos por ningún consumidor de este grupo
            messages = await self.client.xreadgroup(group, consumer, {stream: ">"}, count=count)
            results = []
            if messages:
                for stream_name, events in messages:
                    for event_id, event_data in events:
                        results.append((event_id, json.loads(event_data["data"])))
            return results
        return await self._retry_operation(op)

    async def acknowledge(self, stream: str, group: str, *ids: str) -> None:
        if not ids:
            return
        async def op():
            await self.client.xack(stream, group, *ids)
        await self._retry_operation(op)

    # --- CACHÉ ---

    async def cache_get(self, key: str) -> Optional[dict]:
        async def op():
            data = await self.client.get(key)
            if data:
                return json.loads(data)
            return None
        return await self._retry_operation(op)

    async def cache_set(self, key: str, value: dict, ttl: int) -> None:
        async def op():
            await self.client.set(key, json.dumps(value), ex=ttl)
        await self._retry_operation(op)

    async def cache_exists(self, key: str) -> bool:
        async def op():
            return await self.client.exists(key) > 0
        return await self._retry_operation(op)

    async def cache_expire(self, key: str, ttl: int) -> None:
        """Renueva TTL de una clave sin cambiar el valor (útil para misp:meta)."""
        async def op():
            await self.client.expire(key, ttl)
        await self._retry_operation(op)

    async def misp_hit_record(self) -> None:
        """Registra un hit de enrichment MISP en ventana deslizante 24h (ZSET por timestamp)."""
        async def op():
            now = time.time()
            cutoff = now - 86400
            member = f"{now:.6f}:{uuid.uuid4().hex}"
            await self.client.zadd(self.MISP_HITS_ZSET, {member: now})
            await self.client.zremrangebyscore(self.MISP_HITS_ZSET, "-inf", cutoff)
        await self._retry_operation(op)

    async def misp_hits_count_24h(self) -> int:
        """Cantidad de hits MISP registrados en las últimas 24h (tras limpiar entradas viejas)."""
        async def op():
            now = time.time()
            cutoff = now - 86400
            await self.client.zremrangebyscore(self.MISP_HITS_ZSET, "-inf", cutoff)
            return int(await self.client.zcard(self.MISP_HITS_ZSET))
        return await self._retry_operation(op)

    # --- SETS (Blocklists) ---

    async def blocklist_add(self, lista: str, *valores: str) -> None:
        if not valores: return
        async def op():
            await self.client.sadd(f"blocklist:{lista}", *valores)
        await self._retry_operation(op)

    async def blocklist_check(self, lista: str, valor: str) -> bool:
        async def op():
            return await self.client.sismember(f"blocklist:{lista}", valor)
        return await self._retry_operation(op)

    async def blocklist_size(self, lista: str) -> int:
        async def op():
            return await self.client.scard(f"blocklist:{lista}")
        return await self._retry_operation(op)

    # --- PUB/SUB ---

    async def publish_alert(self, canal: str, data: dict) -> None:
        async def op():
            await self.client.publish(canal, json.dumps(data))
        await self._retry_operation(op)

    async def subscribe_alerts(self, canal: str, callback: Callable) -> None:
        async def op():
            pubsub = self.client.pubsub()
            await pubsub.subscribe(canal)
            logger.info(f"Suscrito a canal PubSub: {canal}")
            try:
                async for message in pubsub.listen():
                    if message["type"] == "message":
                        await callback(json.loads(message["data"]))
            except Exception as e:
                logger.error(f"Error procesando mensajes PubSub en {canal}: {e}")
                raise
            finally:
                await pubsub.unsubscribe(canal)
        await self._retry_operation(op)
