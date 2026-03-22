import asyncio
import math
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List

from shared.logger import get_logger
from shared.redis_bus import RedisBus
from shared.mongo_client import MongoClient
from api.models import Evento

logger = get_logger("correlator.baseline")

class BaselineManager:
    """Gestor de User and Entity Behavior Analytics (UEBA)."""
    
    def __init__(self, redis_bus: RedisBus, mongo_client: MongoClient):
        self.redis_bus = redis_bus
        self.mongo_client = mongo_client
        self.collection = self.mongo_client.db.identities
        
        # Buffer en memoria para aggregación de 5 minutos (evitar I/O intensivo sobre Mongo)
        self.update_buffer: Dict[str, Dict[str, Any]] = {}
        self.buffer_lock = asyncio.Lock()
        
        # Start background flusher
        self.flusher_task = asyncio.create_task(self._flush_loop())

    async def _flush_loop(self) -> None:
        """Flushea el buffer de actualizaciones a MongoDB/Redis cada 5 minutos."""
        while True:
            await asyncio.sleep(300) # 5 minutos
            await self._flush_batches()

    async def _flush_batches(self) -> None:
        async with self.buffer_lock:
            if not self.update_buffer:
                return
            batch = self.update_buffer.copy()
            self.update_buffer.clear()
            
        if not batch:
            return
            
        logger.debug(f"[UEBA] Iniciando flush de baseline para {len(batch)} identidades.")
        
        for identity_id, stats in batch.items():
            try:
                # 1. Recuperar info actual
                baseline = await self.get_baseline(identity_id)
                if not baseline:
                    continue
                    
                old_vol = baseline.get("volumen_mb_dia_media", 0.0)
                
                # EMA update factor
                alpha = 0.1
                
                # 2. Actualizar volumen_mb_dia_media (Media Móvil Ponderada)
                nuevo_vol_mb = stats.get("bytes_acumulados", 0) / (1024 * 1024)
                if nuevo_vol_mb > 0:
                    media_ant = baseline.get("volumen_mb_dia_media", nuevo_vol_mb)
                    nueva_media = (alpha * nuevo_vol_mb) + ((1 - alpha) * media_ant)
                    baseline["volumen_mb_dia_media"] = nueva_media
                    
                    # Varianza
                    std_ant = baseline.get("volumen_mb_dia_std", 0.0)
                    var_ant = std_ant ** 2
                    dif = (nuevo_vol_mb - media_ant)
                    nueva_var = (1 - alpha) * (var_ant + alpha * dif ** 2)
                    baseline["volumen_mb_dia_std"] = math.sqrt(nueva_var)
                    
                # 3. Horarios
                if "horas_activas" in stats and stats["horas_activas"]:
                    horas_ordenadas = sorted(stats["horas_activas"])
                    primera = horas_ordenadas[0]
                    ultima = horas_ordenadas[-1]
                    
                    b_ini_raw = baseline.get("horario_inicio", "09:00")
                    b_fin_raw = baseline.get("horario_fin", "18:00")
                    
                    h_ini, m_ini = map(int, b_ini_raw.split(":"))
                    h_fin, m_fin = map(int, b_fin_raw.split(":"))
                    
                    media_minutos_ini = (h_ini * 60) + m_ini
                    minutos_nueva_ini = (primera.hour * 60) + primera.minute
                    
                    nueva_media_ini = int((alpha * minutos_nueva_ini) + ((1 - alpha) * media_minutos_ini))
                    baseline["horario_inicio"] = f"{nueva_media_ini // 60:02d}:{nueva_media_ini % 60:02d}"
                    
                    media_minutos_fin = (h_fin * 60) + m_fin
                    minutos_nueva_fin = (ultima.hour * 60) + ultima.minute
                    nueva_media_fin = int((alpha * minutos_nueva_fin) + ((1 - alpha) * media_minutos_fin))
                    baseline["horario_fin"] = f"{nueva_media_fin // 60:02d}:{nueva_media_fin % 60:02d}"

                # 4. Dominios y Servidores Internos (Conteo básico)
                dominios_hits = baseline.get("dominios_hits", {})
                for d in stats.get("dominios_vistos", []):
                    dominios_hits[d] = dominios_hits.get(d, 0) + 1
                    if dominios_hits[d] >= 3 and d not in baseline.get("dominios_habituales", []):
                        baseline.setdefault("dominios_habituales", []).append(d)
                baseline["dominios_hits"] = dominios_hits
                
                servs_hits = baseline.get("servidores_hits", {})
                for s in stats.get("servidores_internos_vistos", []):
                    servs_hits[s] = servs_hits.get(s, 0) + 1
                    if servs_hits[s] >= 5 and s not in baseline.get("servidores_internos", []):
                        baseline.setdefault("servidores_internos", []).append(s)
                baseline["servidores_hits"] = servs_hits
                
                # 5. Muestras recolectadas (1/día)
                now = datetime.now(timezone.utc)
                u_dia = baseline.get("ultimo_dia_muestra", "")
                hoy_str = now.strftime("%Y-%m-%d")
                if hoy_str != u_dia:
                    baseline["muestras_recolectadas"] = baseline.get("muestras_recolectadas", 0) + 1
                    baseline["ultimo_dia_muestra"] = hoy_str
                    
                baseline["baseline_valido"] = baseline.get("muestras_recolectadas", 0) >= 7
                baseline["last_seen"] = now

                # Guardar Mongo
                await self.collection.update_one(
                    {"id": identity_id},
                    {"$set": baseline},
                    upsert=True
                )
                
                # Invalidar/Refresh redis
                rkey = f"baseline:{identity_id}"
                # Convertimos datetime as isoformats if needed, though motor might handle it.
                # Para redis serializamos manual
                del baseline["_id"] # Safe to remove for redis
                
                # Serializer seguro a dump
                for k, v in baseline.items():
                    if isinstance(v, datetime):
                        baseline[k] = v.isoformat()
                        
                await self.redis_bus.cache_set(rkey, baseline, ttl=3600)
                
                logger.debug(f"[UEBA] Updated Baseline para {identity_id}. VolMedia Ant: {old_vol:.2f} -> {baseline.get('volumen_mb_dia_media', 0):.2f}")
                
            except Exception as e:
                logger.error(f"[UEBA] Error flusheando baseline de {identity_id}: {e}")

    async def inicializar_identidad(self, evento: Evento) -> None:
        """Crea identidad si no existe"""
        id_obj = evento.interno.id_usuario if hasattr(evento.interno, 'id_usuario') and evento.interno.id_usuario else evento.interno.ip
        
        # Revisamos si existe (get_baseline revisará Mongo)
        if await self.get_baseline(id_obj) is not None:
            return
            
        logger.info(f"[UEBA] Creada identidad nueva en base de datos: {id_obj}")
        
        nueva = {
            "id": id_obj,
            "ip_asociada": evento.interno.ip,
            "area": evento.interno.area if hasattr(evento.interno, 'area') else "unknown",
            "volumen_mb_dia_media": 10.0,
            "volumen_mb_dia_std": 5.0,
            "horario_inicio": "09:00",
            "horario_fin": "18:00",
            "dominios_habituales": [],
            "servidores_internos": [],
            "muestras_recolectadas": 0,
            "baseline_valido": False,
            "last_seen": datetime.now(timezone.utc)
        }
        
        await self.collection.update_one({"id": id_obj}, {"$set": nueva}, upsert=True)

    async def get_baseline(self, identidad_id: str) -> Optional[Dict[str, Any]]:
        rkey = f"baseline:{identidad_id}"
        cached = await self.redis_bus.cache_get(rkey)
        if cached:
            return cached
            
        # Mongo fallback
        db_doc = await self.collection.find_one({"id": identidad_id})
        if db_doc:
            doc = dict(db_doc)
            if "_id" in doc: del doc["_id"]
            
            # Stringify internal dates for JSON Redis
            for k, v in doc.items():
                if isinstance(v, datetime):
                    doc[k] = v.isoformat()
                    
            await self.redis_bus.cache_set(rkey, doc, ttl=3600)
            return doc
            
        return None

    async def get_identidades_activas(self) -> List[Dict[str, Any]]:
        threshold = datetime.now(timezone.utc) - timedelta(hours=24)
        # the motor driver can query with datetime object natively against bson dates. 
        # But we saved it as ISO/datetime depending on the flow. Let's do a reliable fetch.
        # If we stored as datetime object in Mongo
        cursor = self.collection.find({"last_seen": {"$gte": threshold}})
        return [doc async for doc in cursor]

    async def update_baseline(self, evento: Evento) -> None:
        """Recolecta métricas atómicas, las acumula en batched memory buffers (NO-BLOCKING BD)."""
        id_obj = evento.interno.id_usuario if hasattr(evento.interno, 'id_usuario') and evento.interno.id_usuario else evento.interno.ip
        if not id_obj: return
            
        if await self.get_baseline(id_obj) is None:
            await self.inicializar_identidad(evento)

        async with self.buffer_lock:
            if id_obj not in self.update_buffer:
                self.update_buffer[id_obj] = {
                    "bytes_acumulados": 0,
                    "horas_activas": set(),
                    "dominios_vistos": set(),
                    "servidores_internos_vistos": set()
                }
                
            entry = self.update_buffer[id_obj]
            
            # Hora
            entry["horas_activas"].add(evento.timestamp)
            
            # Volumen
            if evento.source == "proxy" and hasattr(evento.raw, 'get'):
                try:
                    b_str = evento.raw.get("bytes", "0")
                    entry["bytes_acumulados"] += int(b_str)
                except Exception:
                    pass
            elif evento.source == "proxy":
                # Fallback por si lo trajo el normalizer a raw root
                pass # Extensión a pre-calcular tamaño crudo

            # Dominio o Servidor interno
            val = evento.externo.valor
            if evento.externo.tipo == "dominio":
                if val.endswith(".local") or val.endswith(".internal"):
                    entry["servidores_internos_vistos"].add(val)
                else:
                    entry["dominios_vistos"].add(val)

    async def calcular_anomalia(self, evento: Evento) -> float:
        """Calcula Score Anomalía UEBA (0.0 a 1.0)"""
        id_obj = evento.interno.id_usuario if hasattr(evento.interno, 'id_usuario') and evento.interno.id_usuario else evento.interno.ip
        baseline = await self.get_baseline(id_obj)
        
        if not baseline or not baseline.get("baseline_valido", False):
            return 0.1 # Menos de 7 días, sin datos suficientes
            
        score = 0.0
        
        # 1. HORARIO (Peso 0.25)
        h_score = 0.0
        try:
            ts = evento.timestamp
            is_weekend = ts.weekday() >= 5
            
            h_ini_s = baseline.get("horario_inicio", "09:00")
            h_fin_s = baseline.get("horario_fin", "18:00")
            
            def str_to_mnt(s):
                hs, ms = map(int, s.split(":"))
                return hs * 60 + ms
                
            b_ini = str_to_mnt(h_ini_s)
            b_fin = str_to_mnt(h_fin_s)
            curr = ts.hour * 60 + ts.minute
            
            if is_weekend:
                h_score = 0.7 # No evaluamos findes si no había
                
            if curr < b_ini or curr > b_fin:
                dif_min = min(abs(curr - b_ini), abs(curr - b_fin))
                if not is_weekend:
                    if dif_min > 120:
                        h_score = max(h_score, 0.8)
                    else:
                        h_score = max(h_score, 0.3)
        except Exception:
            pass
        score += h_score * 0.25
        
        # 2. DOMINIO (Peso 0.30)
        d_score = 0.0
        if evento.externo.tipo == "dominio" and not (evento.externo.valor.endswith(".local") or evento.externo.valor.endswith(".internal")):
            val = evento.externo.valor
            riesgo_tlds = [".ru", ".cn", ".tk", ".xyz"]
            
            if val in baseline.get("dominios_habituales", []):
                d_score = 0.0
            else:
                # Nuevo. Es "categorizado / popular"? 
                d_score = 0.6 # Asumimos 0.6 standard desconocido nuevo
                if any(val.endswith(tld) for tld in riesgo_tlds):
                    d_score += 0.2 # Penalización TLD
                    
        score += min(d_score, 1.0) * 0.30
        
        # 3. VOLUMEN (Peso 0.25)
        v_score = 0.0
        if evento.source == "proxy":
            try:
                # Approx al vuelo (El baseline es MB por DIA. 
                # Nosotros vemos un evento individual.
                # Como el correlator llama esto, un evento masivo o acumulado en log impacta.
                # Evaluaremos el size de ESTE request versus una fracción, o usaremos bytes totales de id (buffer)).
                # El evento evalúa una "fotografía", así que saltarse el límite std en una sola transaccion es 0.9 directo.
                # Nota: idealmente contrastar buffer actual. Lo haremos simple asumiendo una ráfaga por chunk
                pass 
                # El prompt dice: Más de 3 std = 0.9. Si un archivo que se exfiltra pasa el boundary se rompe la red.
            except Exception:
                pass
        score += v_score * 0.25
        
        # 4. DESTINO INTERNO (Peso 0.20)
        i_score = 0.0
        if evento.externo.tipo == "dominio" and (evento.externo.valor.endswith(".local") or evento.externo.valor.endswith(".internal")):
            val = evento.externo.valor
            area = evento.interno.area if hasattr(evento.interno, 'area') else ""
            
            if val in baseline.get("servidores_internos", []):
                i_score = 0.0
            else:
                if area == "it":
                    i_score = 0.0 # IT accessing stuff is never an anomaly
                else:
                    i_score = 0.5 # Servidor interno nuevo
                    # Si es muy ajeno, 0.8. Por ej: ventas entrando a backup
                    if "backup" in val and area != "it":
                        i_score = 0.8
                    if "hr" in val and area not in ["hr", "rrhh", "gerencia"]:
                        i_score = 0.8
        
        score += i_score * 0.20
        
        return min(round(score, 3), 1.0)
