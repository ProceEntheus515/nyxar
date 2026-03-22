import os
import uuid
import asyncio
import random
from typing import Optional, List, Tuple, Literal, cast
from urllib.parse import urlparse

from shared.logger import get_logger
from shared.redis_bus import RedisBus
from shared.mongo_client import MongoClient
from shared.heartbeat import heartbeat_loop
from api.models import Evento, Enrichment

from ad_connector.resolver import IdentityResolver

from enricher.cache import EnrichmentCache
from enricher.feeds.downloader import FeedDownloader
from enricher.apis.abuseipdb import AbuseIPDB
from enricher.apis.otx import AlienVaultOTX

logger = get_logger("enricher.engine")

class EnrichmentEngine:
    def __init__(self):
        self.redis_bus = RedisBus()
        self.cache = EnrichmentCache(self.redis_bus)
        self.feeds = FeedDownloader(self.redis_bus)
        self.abuse_ipdb = AbuseIPDB()
        self.otx = AlienVaultOTX()
        
        self.group_name = "enricher-group"
        self.consumer_name = f"enricher-{uuid.uuid4().hex[:8]}"
        self._processed = 0
        self.mongo_client = MongoClient()
        self.identity_resolver: Optional[IdentityResolver] = None

    def _extraer_target(self, evento: Evento) -> Tuple[Optional[str], Optional[str]]:
        """Extrae el valor a enriquecer y clasifica el tipo"""
        ext = evento.externo
        if ext.tipo == "dominio":
            return ext.valor, "dominio"
        elif ext.tipo == "ip":
            return ext.valor, "ip"
        elif ext.tipo == "url":
            # Extraer dominio sucio
            val = ext.valor
            parsed = urlparse(f"http://{val}") if not val.startswith("http") else urlparse(val)
            if parsed.hostname:
                return parsed.hostname.split("/")[0], "dominio"
            return None, None
        elif ext.tipo == "hash":
            return ext.valor, "hash"
            
        return None, None

    def _calcular_risk_score(self, reputacion: str) -> int:
        """Determina un scoring probabilístico estandarizado según reputación."""
        if reputacion == "malicioso":
            return random.randint(70, 90)
        elif reputacion == "sospechoso":
            return random.randint(40, 60)
        elif reputacion == "limpio":
            return random.randint(0, 10)
            
        return 15 # "desconocido" o "timeout"

    async def _enrichment_from_misp(
        self,
        meta_valor: str,
    ) -> Enrichment:
        ctx = await self.redis_bus.cache_get(f"misp:meta:{meta_valor}")
        rep: str = "malicioso"
        if ctx and isinstance(ctx.get("reputacion"), str):
            rep = ctx["reputacion"]
        if rep not in ("limpio", "sospechoso", "malicioso", "desconocido"):
            rep = "malicioso"
        rep_lit = cast(Literal["limpio", "sospechoso", "malicioso", "desconocido"], rep)
        tags: List[str] = []
        categoria = "MISP IOC"
        if ctx:
            raw_tags = ctx.get("tags")
            if isinstance(raw_tags, list):
                tags = [str(t) for t in raw_tags]
            categoria = str(ctx.get("event_name") or categoria)
        await self.redis_bus.misp_hit_record()
        return Enrichment(
            reputacion=rep_lit,
            fuente="misp",
            categoria=categoria,
            tags=tags,
        )

    async def enrich_event(self, evento: Evento) -> Evento:
        try:
            valor, tipo = self._extraer_target(evento)
            if not valor or not tipo:
                return evento
                
            # PASO 2: Verificar Caché
            cached = await self.cache.get_enrichment(valor)
            if cached:
                await self.cache.record_hit()
                return evento.model_copy(update={
                    "enrichment": cached,
                    "risk_score": self._calcular_risk_score(cached.reputacion)
                })
                
            await self.cache.record_miss()

            # PASO 3: Blocklists Locales Ultrarrápidas
            enrich_obj = None
            match_local: Optional[str] = None

            if tipo == "ip":
                match_local = await self.feeds.check_ip(valor)
            elif tipo == "dominio":
                match_local = await self.feeds.check_domain(valor)
            elif tipo == "url":
                match_local = await self.feeds.check_misp_url(evento.externo.valor)
                if not match_local:
                    match_local = await self.feeds.check_domain(valor)
            elif tipo == "hash":
                match_local = await self.feeds.check_misp_hash(evento.externo.valor)

            if match_local:
                if match_local.startswith("misp_"):
                    if match_local == "misp_domains":
                        meta_v = await self.feeds.resolve_misp_domain_match(valor) or valor
                    elif match_local == "misp_urls":
                        meta_v = evento.externo.valor.strip()
                    elif match_local == "misp_hashes":
                        meta_v = evento.externo.valor.strip().lower()
                    else:
                        meta_v = valor
                    enrich_obj = await self._enrichment_from_misp(meta_v)
                else:
                    enrich_obj = Enrichment(
                        reputacion="malicioso",
                        fuente=f"Local Blocklist ({match_local})",
                        tags=[match_local],
                    )

            # PASO 4: Consultar APIs
            if not enrich_obj:
                if tipo == "ip":
                    try:
                        enrich_obj = await self.abuse_ipdb.check_ip(valor)
                    except Exception as e:
                        logger.warning(f"AbuseIPDB falló para {valor}: {e}")
                    
                if not enrich_obj and (tipo == "ip" or tipo == "dominio"):
                    try:
                        enrich_obj = await self.otx.check_indicator(valor, tipo)
                    except Exception as e:
                        logger.warning(f"OTX falló para {valor}: {e}")
                    
                if tipo == "hash":
                    enrich_obj = Enrichment(reputacion="desconocido", fuente="VirusTotal (Skipped)", tags=[])

            # Fallback final
            if not enrich_obj:
                enrich_obj = Enrichment(reputacion="desconocido", fuente="timeout", tags=[])

            # PASO 5: Guardar en caché y retornar copia inmutable correcta
            await self.cache.set_enrichment(valor, enrich_obj)
            
            return evento.model_copy(update={
                "enrichment": enrich_obj,
                "risk_score": self._calcular_risk_score(enrich_obj.reputacion)
            })
            
        except Exception as e:
            logger.error(f"Falla crítica enriqueciendo evento ID={evento.id}: {e}")
            return evento


    async def _procesar_evento(self, evt_id: bytes, raw_dict: dict) -> bytes:
        """Helper para try-catch por el gather en la pipeline map-reduce"""
        try:
            # Rehidratar el model desde raw log parseado por normalizer
            from collector.normalizer import Normalizer
            norm = Normalizer(
                self.redis_bus,
                resolver=self.identity_resolver,
            )
            
            # Nota: el stream RAW trae formates de "dns", "proxy" que ya pasaron por Normalizer en collector?
            # Si el collector ya aplicó Pydantic -> lo leemos.
            # Según diseño: collector -> raw
            # Esperamos que Evento** dicte estrucutra limpia
            
            if "id" not in raw_dict:
                # El bus recibió json puro
                parsed_evento = await norm.normalize(raw_dict.get("raw", raw_dict), raw_dict.get("source", "unknown"))
                if not parsed_evento:
                    return evt_id
            else:
                parsed_evento = Evento(**raw_dict)
                
            enriquecido = await self.enrich_event(parsed_evento)
            
            # Paso 2 del Loop: Republicar
            await self.redis_bus.publish_event(self.redis_bus.STREAM_ENRICHED, enriquecido.model_dump(mode="json")) # Serializar fechas via Pydantic native
            return evt_id
        except Exception as e:
            logger.error(f"Failed enrichment payload procesing en consumer: {e}")
            return evt_id

    async def run(self):
        logger.info(f"Conectando EnrichmentEngine (Consumer: {self.consumer_name})...")
        await self.redis_bus.connect()
        await self.mongo_client.connect()
        self.identity_resolver = IdentityResolver(self.redis_bus, self.mongo_client)

        # Lanzar paralelamente el scheduler de listas en este mismo worker
        asyncio.create_task(self.feeds.start_scheduler())
        hb_task = asyncio.create_task(heartbeat_loop(self.redis_bus, "enricher"), name="enricher-hb")

        try:
            while True:
                try:
                    eventos = await self.redis_bus.consume_events(
                        self.redis_bus.STREAM_RAW,
                        self.group_name,
                        self.consumer_name,
                        count=10,
                    )

                    if not eventos:
                        await asyncio.sleep(0.1)
                        continue

                    tasks = []
                    for b_msg_id, raw_dict in eventos:
                        tasks.append(self._procesar_evento(b_msg_id, raw_dict))

                    resultados_msg_id = await asyncio.gather(*tasks, return_exceptions=True)

                    ids_a_ackear = [
                        r for r in resultados_msg_id if not isinstance(r, BaseException)
                    ]
                    if ids_a_ackear:
                        await self.redis_bus.acknowledge(
                            self.redis_bus.STREAM_RAW,
                            self.group_name,
                            *[str(x) for x in ids_a_ackear],
                        )

                    self._processed += len(ids_a_ackear)
                    if self._processed >= 100:
                        logger.info(
                            "Enricher Throughput: 100 eventos despachados hacia STREAMS_ENRICHED."
                        )
                        self._processed = 0

                except Exception as e:
                    logger.error(f"Error loop principal Enricher: {e}")
                    await asyncio.sleep(2)
        finally:
            hb_task.cancel()
            try:
                await hb_task
            except asyncio.CancelledError:
                pass
            await self.redis_bus.disconnect()
            await self.mongo_client.disconnect()

if __name__ == "__main__":
    from shared.logger import get_logger
    import logging
    
    # Asegurar modo prod config via envs
    app = EnrichmentEngine()
    
    # Manejo de OS signal intercept fallback
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(app.run())
    except KeyboardInterrupt:
        logger.info("Enricher apagado manualmente.")
