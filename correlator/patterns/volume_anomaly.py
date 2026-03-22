import uuid
from typing import Optional
from datetime import datetime, timezone

from shared.logger import get_logger
from shared.redis_bus import RedisBus
from api.models import Evento

from .base import BasePattern, Incidente

logger = get_logger("correlator.patterns.volume")

class VOLUMEANOMALYPattern(BasePattern):
    name = "Volumen Anormal / Posible Exfiltración"
    description = "Tráfico extrínseco superando la heurística base horario, sumado a abusos asimétricos hacia nubes públicas."
    mitre_technique = "T1048"

    async def check(self, evento: Evento, contexto: dict) -> Optional[Incidente]:
        if evento.source != "proxy" or not hasattr(evento, "raw") or not evento.raw:
            return None
            
        b_str = evento.raw.get("bytes", "0")
        try:
            bytes_sent = int(b_str)
        except ValueError:
            return None
            
        ip = evento.interno.ip
        now = datetime.now(timezone.utc)
        hora = now.hour
        
        redis_bus: RedisBus = contexto["redis_bus"]
        baseline = contexto.get("baseline", {})
        
        r = redis_bus.client
        if not r: return None
        
        # Cloud Tracker (30 mins TTL list)
        cloud_services = ["drive.google.com", "dropbox.com", "mega.nz", "wetransfer.com", "onedrive.live.com"]
        destino = evento.externo.valor
        if destino in cloud_services:
            ckey = f"pattern:cloud:{ip}"
            await r.rpush(ckey, str(now.timestamp()))
            await r.expire(ckey, 1800) # 30 mins
            
            # Limpiar items viejos
            items = await r.lrange(ckey, 0, -1)
            cutoff = now.timestamp() - 1800
            valid_items = [i for i in items if float(i.decode()) > cutoff]
            if len(valid_items) > 15: # "Muchas conexiones < 30 min"
                return Incidente(
                    id=f"INC-{uuid.uuid4().hex[:8]}",
                    timestamp=now,
                    patron=self.name,
                    mitre_technique=self.mitre_technique,
                    descripcion=f"Rafága excesiva de subidas a la nube ({len(valid_items)} peticiones a servicios públicos en <30min)",
                    severidad="ALTA", # type: ignore
                    host_afectado=ip,
                    evento_original_id=evento.id,
                    detalles={"total_conns_nube": len(valid_items), "ultimo_destino": destino}
                )

        # Volumetria Por Hora
        vkey = f"pattern:volume:{ip}:{hora}"
        mb_added = bytes_sent / (1024 * 1024)
        
        acc_mb = await r.incrbyfloat(vkey, mb_added)
        await r.expire(vkey, 3600) # El bucket de esta hora expira tras una hora sin toques
        
        # Comparar Baseline
        baseline_valid = baseline.get("baseline_valido", False)
        if not baseline_valid:
            return None
            
        media_dia = baseline.get("volumen_mb_dia_media", 100.0)
        # Asumiendo dia laboral tipico de 9h
        media_hora = media_dia / 9.0 
        
        # 5x Volumen Promedio
        if acc_mb > (media_hora * 5):
            await r.delete(vkey) # Reseteo para no spamear
            return Incidente(
                id=f"INC-{uuid.uuid4().hex[:8]}",
                timestamp=now,
                patron=self.name,
                mitre_technique=self.mitre_technique,
                descripcion=f"Exfiltración detectada: Ancho de banda saliendo ({acc_mb:.1f} MB/h) supera >5x el promedio diario.",
                severidad="CRÍTICA", # type: ignore
                host_afectado=ip,
                evento_original_id=evento.id,
                detalles={"mb_acumulados": round(acc_mb, 2), "media_esperada": round(media_hora, 2)}
            )
            
        # 3x pero fuera de Horario
        es_fuera_horario = False
        h_ini, m_ini = map(int, baseline.get("horario_inicio", "09:00").split(":"))
        h_fin, m_fin = map(int, baseline.get("horario_fin", "18:00").split(":"))
        if hora < h_ini or hora > h_fin:
            es_fuera_horario = True
            
        if es_fuera_horario and acc_mb > (media_hora * 3):
             await r.delete(vkey)
             return Incidente(
                id=f"INC-{uuid.uuid4().hex[:8]}",
                timestamp=now,
                patron=self.name,
                mitre_technique=self.mitre_technique,
                descripcion=f"Pico de transferencia nocturna o ajena a horario laboral (>3x del base). Total: {acc_mb:.1f} MB/h",
                severidad="MEDIA", # type: ignore
                host_afectado=ip,
                evento_original_id=evento.id,
                detalles={"mb_acumulados": round(acc_mb, 2), "media_esperada": round(media_hora, 2)}
            )

        return None
