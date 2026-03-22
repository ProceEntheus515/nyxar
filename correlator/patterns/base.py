import uuid
from typing import Optional, Literal
from datetime import datetime
from pydantic import BaseModel
from api.models import Evento

class Incidente(BaseModel):
    id: str
    timestamp: datetime
    patron: str
    mitre_technique: str
    descripcion: str
    severidad: Literal["BAJA", "MEDIA", "ALTA", "CRITICA", "CRÍTICA"]
    host_afectado: str
    evento_original_id: str
    detalles: dict

class BasePattern:
    name: str
    description: str
    mitre_technique: str
    
    async def check(self, evento: Evento, contexto: dict) -> Optional[Incidente]:
        raise NotImplementedError
