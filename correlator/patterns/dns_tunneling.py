import uuid
import math
from typing import Optional
from datetime import datetime, timezone

from shared.logger import get_logger
from shared.redis_bus import RedisBus
from api.models import Evento

from .base import BasePattern, Incidente

logger = get_logger("correlator.patterns.dns_tunneling")

class DNSTUNNELINGPattern(BasePattern):
    name = "DNS Tunneling"
    description = "Exfiltración de datos encodificados a través de subdominios extremadamente largos o entrópicos."
    mitre_technique = "T1071.004"

    def _calcular_entropia(self, texto: str) -> float:
        """H = -sum(p * log2(p) for cada carácter único)"""
        if not texto:
            return 0.0
        conteo = {}
        for c in texto:
            conteo[c] = conteo.get(c, 0) + 1
        
        entropia = 0.0
        total = len(texto)
        for c, count in conteo.items():
            p = count / total
            entropia -= p * math.log2(p)
            
        return entropia

    def _extraer_subdominio(self, dominio: str) -> str:
        partes = dominio.split(".")
        if len(partes) > 2:
            return ".".join(partes[:-2])
        return ""

    async def check(self, evento: Evento, contexto: dict) -> Optional[Incidente]:
        if evento.source != "dns" or evento.externo.tipo != "dominio":
            return None
            
        dominio_com= evento.externo.valor
        subdominio = self._extraer_subdominio(dominio_com)
        
        if not subdominio:
            return None
            
        # 1. Calculamos metricas basicas
        longitud = len(subdominio)
        entropia = self._calcular_entropia(subdominio)
        
        # Guardar baselines para evaluar la frecuencia de subdominios
        redis_bus: RedisBus = contexto["redis_bus"]
        r = redis_bus.client
        if not r:
            return None
            
        base_domain = ".".join(dominio_com.split(".")[-2:])
        key_freq = f"pattern:dns:{evento.interno.ip}:{base_domain}"
        
        try:
            # Hash o SADD para uniqueness (20 subs distintos en 10 min)
            await r.sadd(key_freq, subdominio)
            await r.expire(key_freq, 600) # 10 minutos
            
            subs_vistos = await r.scard(key_freq)
            
            # CRITERIO Detección CUALQUIERA:
            is_largo = longitud > 45
            is_entropico = entropia > 3.8
            is_burst = subs_vistos > 20
            
            if is_largo or is_entropico or is_burst:
                return Incidente(
                    id=f"INC-{uuid.uuid4().hex[:8]}",
                    timestamp=datetime.now(timezone.utc),
                    patron=self.name,
                    mitre_technique=self.mitre_technique,
                    descripcion=f"Túnel DNS detectado hacia {base_domain}",
                    severidad="ALTA",
                    host_afectado=evento.interno.ip,
                    evento_original_id=evento.id,
                    detalles={
                        "dominio_base": base_domain,
                        "subdominio": subdominio,
                        "longitud": longitud,
                        "entropia": round(entropia, 2),
                        "subdominios_unicos_vistos": subs_vistos,
                        "trigger": "Largo" if is_largo else ("Entrópico" if is_entropico else "Burst")
                    }
                )
        except Exception as e:
            logger.error(f"Fallo detectando DNS Tunneling en {evento.interno.ip}: {e}")
            
        return None
