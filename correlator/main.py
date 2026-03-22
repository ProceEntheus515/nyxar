import uuid
import asyncio
from typing import Optional, List

from shared.logger import get_logger
from shared.redis_bus import RedisBus
from shared.mongo_client import MongoClient
from api.models import Evento

from correlator.baseline import BaselineManager
from correlator.patterns.base import Incidente
from correlator.patterns import PATTERNS

logger = get_logger("correlator.engine")

class CorrelatorEngine:
    def __init__(self):
        self.redis_bus = RedisBus()
        self.mongo_client = MongoClient()
        self.baseline_manager = BaselineManager(self.redis_bus, self.mongo_client)
        
        self.group_name = "correlator-group"
        self.consumer_name = f"correlator-{uuid.uuid4().hex[:8]}"

    def _get_severity_score(self, severidad: str) -> int:
        sev = severidad.upper()
        if sev == "CRÍTICA" or sev == "CRITICA": return 75
        if sev == "ALTA": return 30
        if sev == "MEDIA": return 15
        return 5 # BAJA

    async def _handle_incidente(self, inc: Incidente) -> None:
        """Procesa y guarda un nuevo incidente garantizado ser único"""
        try:
            # 1. Deduplicación (Anti-Spam) Mismo host, mismo patron, < 30 mins
            r = self.redis_bus.client
            if not r: return
            
            dkey = f"alert:{inc.patron}:{inc.host_afectado}"
            is_dupe = await r.exists(dkey)
            if is_dupe:
                return
                
            # Registrar bloqueo de 30 mins
            await r.set(dkey, "1", ex=1800)
            
            logger.critical(f"ALERTA GENERADA - Host: {inc.host_afectado} | Patron: {inc.patron} | Severidad: {inc.severidad} | Mitre: {inc.mitre_technique}")

            # 2. Publicar al canal que consume api/websocket (redis_listener)
            await self.redis_bus.publish_alert("alerts", inc.model_dump(mode="json"))
            
            # 3. Guardar permanente en MongoDB
            inc_dict = inc.model_dump(mode="json")
            await self.mongo_client.db.incidents.insert_one(inc_dict)

            # 4. Actualizar score de la identidad
            incremento = self._get_severity_score(inc.severidad)
            
            # Update Identity risk_score
            col = self.mongo_client.db.identities
            await col.update_one(
                {"id": inc.host_afectado}, # Generalmente agrupamos en id
                {
                    "$inc": {"risk_score": incremento},
                    "$set": {"last_alert_id": inc.id, "last_alert_ts": inc.timestamp.isoformat()}
                }
            )
        except Exception as e:
            logger.error(f"Fallo salvando incidente {inc.id}: {e}")

    async def _procesar_evento(self, msg_id: bytes, raw: dict) -> bytes:
        try:
            if "externo" not in raw or "interno" not in raw:
                # Fallback de malformación? Si no lo parseó el enricher bien.
                evento = Evento(**raw) 
            else:
                evento = Evento(**raw)
                
            # 1. Update Asincrono de Baselines Locales del UEBA (No-blocking ya que lockea buffer en memoria nomas)
            await self.baseline_manager.update_baseline(evento)
            
            # 2. Obtención de Contexto Inyector para Corutinas Limpias
            id_obj = evento.interno.id_usuario if hasattr(evento.interno, "id_usuario") and evento.interno.id_usuario else evento.interno.ip
            baseline = await self.baseline_manager.get_baseline(id_obj)
            
            ctx = {
                "redis_bus": self.redis_bus,
                "baseline": baseline or {}
            }
            
            # 3. Lanzar PATTERNS check masivo en paralelo (100ms limite total map-reduce)
            # Requisito "no hagas que un patrón tarde > 100ms"
            tasks = []
            for pat in PATTERNS:
                # Empaquetamos en corutinas limitables nativas
                tasks.append(asyncio.wait_for(pat.check(evento, ctx), timeout=0.100))
                
            resultados = await asyncio.gather(*tasks, return_exceptions=True)
            
            alert_tasks = []
            for res in resultados:
                if isinstance(res, Incidente):
                    alert_tasks.append(self._handle_incidente(res))
                elif isinstance(res, asyncio.TimeoutError):
                    logger.warning(f"[CORRELATOR] Time-Out Limit Rebasado: un patróm demoró >100ms")
                elif isinstance(res, Exception):
                    logger.error(f"[CORRELATOR] Patrón crasheó la evaluación aislada: {res}")
                    
            if alert_tasks:
                await asyncio.gather(*alert_tasks)
                
            return msg_id
            
        except Exception as e:
            logger.error(f"Fallo procesando Correlacion Evento: {e}")
            return msg_id

    async def run(self):
        logger.info(f"Conectando CorrelatorEngine (Consumer: {self.consumer_name})...")
        await self.redis_bus.connect()
        await self.mongo_client.connect()
        
        while True:
            try:
                # Enriched Stream Consumer
                eventos = await self.redis_bus.consume_events(
                    self.redis_bus.STREAM_ENRICHED,
                    self.group_name,
                    self.consumer_name,
                    count=20
                )
                
                if not eventos:
                    await asyncio.sleep(0.1)
                    continue
                    
                ops = [self._procesar_evento(mid, raw) for mid, raw in eventos]
                procesados = await asyncio.gather(*ops, return_exceptions=True)
                
                acks = [p for p in procesados if isinstance(p, bytes)]
                if acks:
                    await self.redis_bus.acknowledge(self.redis_bus.STREAM_ENRICHED, self.group_name, acks)

            except Exception as e:
                logger.error(f"Loop error Correlator: {e}")
                await asyncio.sleep(2)

if __name__ == "__main__":
    app = CorrelatorEngine()
    try:
        asyncio.run(app.run())
    except KeyboardInterrupt:
        logger.info("Correlador apagado.")
