import uuid
from typing import Optional
from datetime import datetime, timezone

from shared.logger import get_logger
from shared.redis_bus import RedisBus
from api.models import Evento

from .base import BasePattern, Incidente

logger = get_logger("correlator.patterns.lateral_mov")

class LATERALMOVEMENTPattern(BasePattern):
    name = "Movimiento Lateral (Escaneo Horizontal o DC Access)"
    description = "Detecta ráfagas de escaneos de subred, conexiones anómalas a servicios de admin, o a Domain Controllers."
    mitre_technique = "T1021"

    async def check(self, evento: Evento, contexto: dict) -> Optional[Incidente]:
        if evento.source != "firewall":
            return None
            
        ip_origen = evento.interno.ip
        destino = evento.externo.valor
        
        # Ignorar internet
        is_interno = evento.externo.tipo == "ip" and "192.168." in destino or destino.endswith(".local") or destino.endswith(".internal")
        if not is_interno:
            return None
        
        redis_bus: RedisBus = contexto["redis_bus"]
        baseline = contexto.get("baseline", {})
        r = redis_bus.client
        if not r:
            return None
            
        puertos_admin = ["22", "445", "3389", "5985", "5986"]
        es_dc = "dc01" in destino.lower()
        area = evento.interno.area if hasattr(evento.interno, 'area') else "unknown"
        area = str(area).lower()
        
        puerto_destino = ""
        if hasattr(evento.raw, "get"):
            puerto_destino = str(evento.raw.get("dst_port", ""))
        
        # Detectar Regla B: Conexión DC
        if es_dc:
            # Vimos si no está en sus servers habituales del baseline
            hab_servers = baseline.get("servidores_internos", [])
            if area != "it" and not any("dc01" in s.lower() for s in hab_servers):
                return Incidente(
                    id=f"INC-{uuid.uuid4().hex[:8]}",
                    timestamp=datetime.now(timezone.utc),
                    patron=self.name,
                    mitre_technique=self.mitre_technique,
                    descripcion=f"Conexión directa anómala al controlador de dominio primario (DC01) desde área {area}",
                    severidad="CRÍTICA", # type: ignore
                    host_afectado=ip_origen,
                    evento_original_id=evento.id,
                    detalles={"destino": destino, "puerto": puerto_destino, "regla": "Regla de Oro DC"}
                )
                
        # Detectar Regla C: Puerto Admin desde no IT
        if puerto_destino in puertos_admin and area != "it":
            return Incidente(
                id=f"INC-{uuid.uuid4().hex[:8]}",
                timestamp=datetime.now(timezone.utc),
                patron=self.name,
                mitre_technique=self.mitre_technique,
                descripcion=f"Intento de conexión a puerto administrativo ({puerto_destino}) desde área no IT ({area})",
                severidad="MEDIA", # type: ignore
                host_afectado=ip_origen,
                evento_original_id=evento.id,
                detalles={"destino": destino, "puerto": puerto_destino}
            )
            
        # Detectar Regla A: Escaneo Set Crece (Ult 2 horas)
        try:
            key = f"pattern:lateral:{ip_origen}"
            await r.sadd(key, destino)
            await r.expire(key, 7200) # 2 horas TTL
            
            contactadas = await r.scard(key)
            
            # Reset contador asincronamente si explota el limite
            if contactadas > 5:
                
                # Para evitar duplicados en rafagas 
                await r.delete(key) 
                
                return Incidente(
                    id=f"INC-{uuid.uuid4().hex[:8]}",
                    timestamp=datetime.now(timezone.utc),
                    patron=self.name,
                    mitre_technique=self.mitre_technique,
                    descripcion=f"Posible escaneo de red. Trató de acceder a {contactadas} IPs internas en menos de 2h.",
                    severidad="ALTA", # type: ignore
                    host_afectado=ip_origen,
                    evento_original_id=evento.id,
                    detalles={"total_ips": contactadas, "regla": "Umbral de Escaneo Multi-Host"}
                )
        except Exception as e:
            logger.error(f"Falla en lateral_movement de Redis: {e}")
            
        return None
