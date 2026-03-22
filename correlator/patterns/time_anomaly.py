import uuid
from typing import Optional
from datetime import datetime, timezone

from shared.logger import get_logger
from api.models import Evento

from .base import BasePattern, Incidente

logger = get_logger("correlator.patterns.time_anomaly")

class TIMEANOMALYPattern(BasePattern):
    name = "Anomalía Horaria del Usuario"
    description = "Intrusión potencial o cuenta comprometida empleada fuera del horario laboral histórico del agente."
    mitre_technique = "T1078"

    async def check(self, evento: Evento, contexto: dict) -> Optional[Incidente]:
        baseline = contexto.get("baseline", {})
        
        # Debe tener baseline estable (>7 dias)
        if not baseline.get("baseline_valido", False):
            return None
            
        ip = evento.interno.ip
        area = evento.interno.area if hasattr(evento.interno, 'area') else "unknown"
        ts = evento.timestamp
        hora = ts.hour
        is_weekend = ts.weekday() >= 5
        
        h_ini, m_ini = map(int, baseline.get("horario_inicio", "09:00").split(":"))
        h_fin, m_fin = map(int, baseline.get("horario_fin", "18:00").split(":"))
        
        b_ini_min = h_ini * 60 + m_ini
        b_fin_min = h_fin * 60 + m_fin
        curr_min = ts.hour * 60 + ts.minute
        
        # Validar si está fuera de horario general
        es_fuera_horario = False
        minutos_diferencia = 0
        
        if curr_min < b_ini_min:
            es_fuera_horario = True
            minutos_diferencia = b_ini_min - curr_min
        elif curr_min > b_fin_min:
            es_fuera_horario = True
            minutos_diferencia = curr_min - b_fin_min
            
        if is_weekend:
            # Los fines de semana son fuera de horario, salvo que este acostumbrado
            dias_activos = baseline.get("dias_laborales", [])
            if "sab" not in dias_activos and "dom" not in dias_activos:
                es_fuera_horario = True
                minutos_diferencia = max(minutos_diferencia, 180) # Asume >3hr por ser finde completo

        # Falsos Positivos supresores
        umbral_tolerancia = 0
        if area.lower() in ["it", "gerencia"]:
            umbral_tolerancia = 120 # IT/Gerencia pueden trabajar 2 horas extras sin salirse
            
        if minutos_diferencia <= umbral_tolerancia and not (is_weekend and umbral_tolerancia == 0):
            return None

        if not es_fuera_horario:
            return None
        
        # Volumen Significativo o Dominio Nuevo?
        is_volumen_alto = False
        is_dominio_nuevo = False
        
        if evento.source == "proxy" and hasattr(evento, "raw") and evento.raw:
            try:
                b = int(evento.raw.get("bytes", "0"))
                if b > 10 * 1024 * 1024:
                    is_volumen_alto = True
            except ValueError:
                pass
                
        if evento.externo.tipo == "dominio":
            hab = baseline.get("dominios_habituales", [])
            val = evento.externo.valor
            if val not in hab and not (val.endswith(".local") or val.endswith(".internal")):
                is_dominio_nuevo = True
                
        if not (is_volumen_alto or is_dominio_nuevo):
            # Es fuera de horario, pero es actividad blanda (Ej un ping normal o un update en background)
            return None
            
        # Determinar Severidad (Madrugada, Finde o Variación Larga)
        if 0 <= hora <= 5:
            sev = "ALTA"
        elif is_weekend:
            sev = "MEDIA"
        else:
            if minutos_diferencia > 180: # > ±3h
                sev = "BAJA"
            else:
                return None # Ignorado
                
        return Incidente(
            id=f"INC-{uuid.uuid4().hex[:8]}",
            timestamp=datetime.now(timezone.utc),
            patron=self.name,
            mitre_technique=self.mitre_technique,
            descripcion="Actividad detectada fuera de horario con alto volumen de red o hacia un nuevo dominio.",
            severidad=sev, # type: ignore
            host_afectado=ip,
            evento_original_id=evento.id,
            detalles={"volumen_alto": is_volumen_alto, "dominio_nuevo": is_dominio_nuevo, "area": area}
        )
