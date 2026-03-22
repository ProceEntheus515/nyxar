import uuid
import math
from typing import Optional
from datetime import datetime, timezone
import statistics

from shared.logger import get_logger
from shared.redis_bus import RedisBus
from api.models import Evento

from .base import BasePattern, Incidente

logger = get_logger("correlator.patterns.beaconing")

class BEACONINGPattern(BasePattern):
    name = "Beaconing (C2 Communication)"
    description = "Detección de malware llamando a su servidor de Control & Command (C2) con intervalos regulares."
    mitre_technique = "T1071.001"

    async def check(self, evento: Evento, contexto: dict) -> Optional[Incidente]:
        # Filtrar solo conexiones a dominios externos
        if evento.externo.tipo != "dominio" or (evento.externo.valor.endswith(".local") or evento.externo.valor.endswith(".internal")):
            return None
            
        redis_bus: RedisBus = contexto["redis_bus"]
        r = redis_bus.client
        if not r:
            return None
            
        ip = evento.interno.ip
        domain = evento.externo.valor
        ts = evento.timestamp.timestamp()
        
        key = f"pattern:beacon:{ip}:{domain}"
        
        try:
            # 1. Mantener ultimos 20 timestamps en Redis Sorted Set
            await r.zadd(key, {str(ts): ts})
            # Trim para dejar solo los ultimos 20
            await r.zremrangebyrank(key, 0, -21)
            # Expira a las 24 hs (para no llenarse de keys viejas)
            await r.expire(key, 86400)
            
            # Obtener elementos
            miembros = await r.zrange(key, 0, -1)
            timestamps = [float(m.decode() if isinstance(m, bytes) else float(m)) for m in miembros]
            
            # 2. Si hay 5 o mas consultas, evaluar CV
            count = len(timestamps)
            if count >= 5:
                # Calcular gaps (intervalos de tiempo entre pings consecutivos)
                # Como es un sorted set, ya están ordenados por tiempo
                intervalos = [timestamps[i] - timestamps[i-1] for i in range(1, count)]
                
                mean_gap = statistics.mean(intervalos)
                # Puede ser que envíen tan rápido agrupado que std de 0
                if mean_gap <= 0.1: 
                    return None # Burst inmediato, no es beaconing tipico
                    
                std_gap = statistics.stdev(intervalos) if len(intervalos) > 1 else 0.0
                
                cv = std_gap / mean_gap
                
                # 3. CRITERIO DETECCIÓN: CV < 0.15 y count > 5
                if cv < 0.15:
                    # Severidad según frecuencia
                    if mean_gap < 60:
                        sev = "CRÍTICA"
                    elif mean_gap < 300:
                        sev = "ALTA"
                    else:
                        sev = "MEDIA"
                        
                    return Incidente(
                        id=f"INC-{uuid.uuid4().hex[:8]}",
                        timestamp=datetime.now(timezone.utc),
                        patron=self.name,
                        mitre_technique=self.mitre_technique,
                        descripcion=f"Conexiones C2 altamente regulares (Beaconing) detectadas hacia {domain}",
                        severidad=sev, # type: ignore
                        host_afectado=ip,
                        evento_original_id=evento.id,
                        detalles={
                            "domain": domain,
                            "intervalo_promedio_seg": round(mean_gap, 2),
                            "coeficiente_variacion": round(cv, 3),
                            "hits_detectados": count
                        }
                    )
        except Exception as e:
            logger.error(f"Fallo detectando Beaconing en {ip}: {e}")
            
        return None
