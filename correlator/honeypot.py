import os
import uuid
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from pydantic import BaseModel

from api.models import Evento
from shared.logger import get_logger
from shared.redis_bus import RedisBus
from shared.mongo_client import MongoClient

logger = get_logger("correlator.honeypot")

class HoneypotHit(BaseModel):
    id: str
    timestamp: datetime
    honeypot_name: str
    tipo_honeypot: str
    recurso_tocado: str
    host_atacante: str
    evento_original_id: str
    descripcion: str
    severidad: str = "CRÍTICA" # Los honeypots siempre son críticos por diseño

class HoneypotManager:
    """Implementa recursos trampa indetectables para usuarios reales"""
    
    def __init__(self, redis_bus: RedisBus, mongo_client: MongoClient):
        self.redis_bus = redis_bus
        self.mongo_client = mongo_client
        
        # Base hardcodeada (Se pueden sobreescribir partes parseando config por OS Envs)
        self.HONEYPOTS = {
            "share_financiero": {
                "tipo": "share",
                "indicador": os.getenv("HP_SHARE_FIN", "\\\\fileserver01\\BACKUP_FINANCIERO_2025"),
                "descripcion": "Share de red con nombre atractivo — no existe para usuarios reales"
            },
            "ip_fantasma": {
                "tipo": "ip_fantasma", 
                "indicador": os.getenv("HP_IP_FANTASMA", "192.168.1.254"),
                "descripcion": "IP sin servicios reales — cualquier conexión es sospechosa"
            },
            "usuario_trampa": {
                "tipo": "usuario_ad",
                "indicador": os.getenv("HP_USUARIO_AD", "admin_old"),
                "descripcion": "Usuario de AD deshabilitado — login exitoso imposible legítimamente"
            },
            "dns_trampa": {
                "tipo": "dns_interno",
                "indicador": os.getenv("HP_DNS_INTERNO", "old-erp.empresa.local"),
                "descripcion": "Registro DNS interno que no debería ser consultado"
            }
        }
    
    def _find_indicator(self, evento: Evento, indicador: str) -> bool:
        """Chequea si el indicador se encuentra presente en la red, dominios o el payload crudo"""
        indicator_lower = indicador.lower()
        
        # Check dominios e IPs externas destino
        if evento.externo.valor and indicator_lower in evento.externo.valor.lower():
            return True
            
        # Check source u origins
        if evento.interno.ip and indicator_lower in evento.interno.ip.lower():
            return True
        if hasattr(evento.interno, "id_usuario") and evento.interno.id_usuario and indicator_lower in evento.interno.id_usuario.lower():
            return True
            
        # Revisión profunda del raw payload (ideal para Shares SMB en firewalls/waf, honeypot_share, URLs, payloads proxy)
        if hasattr(evento, "raw") and evento.raw:
            raw_str = str(evento.raw).lower()
            # Double \ formatting match due to json dumps
            if indicator_lower in raw_str or indicator_lower.replace("\\\\", "\\") in raw_str:
                return True
                
        return False

    async def check_event(self, evento: Evento) -> Optional[HoneypotHit]:
        """Verifica cada recurso trampa contra el rastro del evento iterativo."""
        for nombre_hp, config in self.HONEYPOTS.items():
            indicador = config["indicador"]
            
            if self._find_indicator(evento, indicador):
                logger.critical(f"TRAMPA HONEYPOT ACTIVADA - [{nombre_hp}] tocado por {evento.interno.ip}")
                
                hit = HoneypotHit(
                    id=f"HP-{uuid.uuid4().hex[:8]}",
                    timestamp=datetime.now(timezone.utc),
                    honeypot_name=nombre_hp,
                    tipo_honeypot=config["tipo"],
                    recurso_tocado=indicador,
                    host_atacante=evento.interno.ip,
                    evento_original_id=evento.id,
                    descripcion=config["descripcion"]
                )
                
                await self._registrar_hit(hit)
                return hit
                
        return None

    async def _registrar_hit(self, hit: HoneypotHit) -> None:
        """Asienta en BD, envía por Stream (Socket) y destroza el baseline del infractor."""
        try:
            # 1. Guardar en MongoDB (colección honeypot_hits) - Compatible con Change Streams nativos
            hit_dict = hit.model_dump(mode="json")
            await self.mongo_client.db.honeypot_hits.insert_one(hit_dict)
            
            # 2. Publicar Alerta CRÍTICA inmediata por Bus Redis
            alerta_format = {
                "id": hit.id,
                "timestamp": hit.timestamp.isoformat(),
                "patron": "TRAMPILLA_HONEYPOT",
                "mitre_technique": "T1078", # Account abuse / Recon
                "descripcion": f"[HONEYPOT TRIGGER] {hit.descripcion}",
                "severidad": "CRÍTICA",
                "host_afectado": hit.host_atacante,
                "evento_original_id": hit.evento_original_id,
                "detalles": {"recurso": hit.recurso_tocado, "tipo": hit.tipo_honeypot}
            }
            await self.redis_bus.publish_alert("alerts", alerta_format)
            
            # 3. Mínimo 85 en Risk Score para el atacante (Direct Mongo Override)
            col = self.mongo_client.db.identities
            id_obj = hit.host_atacante # Habitualmente el IP, pero el id model puede ser string host
            
            identidad = await col.find_one({"id": id_obj}) # Podriamos filtrar interno.id_usuario sino existe
            score_actual = 0
            if identidad:
                score_actual = identidad.get("risk_score", 0)
                
            nuevo_score = max(score_actual, 85) # Elevar inmediatamente al Rango Critico
            
            await col.update_one(
                {"id": id_obj},
                {
                    "$set": {
                        "risk_score": nuevo_score,
                        "last_alert_id": hit.id,
                        "last_alert_ts": hit.timestamp.isoformat()
                    }
                },
                upsert=True
            )
            
            logger.info(f"Identity Risk Score de {id_obj} sobre-escrito a {nuevo_score} por Honeypot violation.")
            
        except Exception as e:
            logger.error(f"Falla intentando persistir el impacto de Honeypot Hit {hit.id}: {e}")
