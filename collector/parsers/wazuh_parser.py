import asyncio
import hashlib
import os
from typing import Any, Dict, Optional

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import uvicorn

from shared.logger import get_logger
from shared.redis_bus import RedisBus
from shared.wazuh_logons import insert_wazuh_logon_if_applicable, logon_rule_ids
from collector.normalizer import Normalizer

logger = get_logger("collector.parsers.wazuh")

SESSION_CACHE_PREFIX = "identity:session:"


def _logoff_rule_ids() -> set:
    raw = os.getenv("WAZUH_LOGOFF_RULE_IDS", "").strip()
    return {x.strip() for x in raw.split(",") if x.strip()}


class WazuhParser:
    """
    Expone un microservicio FastAPI para recibir webhooks nativos desde Wazuh Manager.
    Convierte el formato alerta JSON directamente y lo pushea a Redis.
    Opcionalmente persiste logons en Mongo (wazuh_logons) para mapa ip->usuario.
    """

    def __init__(
        self,
        redis_bus: RedisBus,
        normalizer: Normalizer,
        mongo_client: Optional[Any] = None,
    ):
        self.redis_bus = redis_bus
        self.mongo_client = mongo_client
        self.normalizer = normalizer
        port_env = os.getenv("WAZUH_WEBHOOK_PORT", "9000")
        self.port = int(port_env)
        self.app = FastAPI(title="Wazuh Webhook Parser")
        self._processed_count = 0

        # Endpoint del Webhook
        @self.app.post("/")
        async def process_webhook(request: Request):
            try:
                # Extraemos el payload asincronamente
                payload = await request.json()
                event_dict = self._parse_line(payload)
                
                if event_dict:
                    # Enviar solo si validó correctamente (rule level >=3 etc)
                    
                    # Deduplicación webhooks (el ID de Wazuh suele identificar el hit único o el timestamp+id)
                    rule_id = payload.get("rule", {}).get("id", "0")
                    agent_ip = payload.get("agent", {}).get("ip", "unknown")
                    ts = payload.get("timestamp", "")
                    
                    h_str = hashlib.md5(f"{ts}-{agent_ip}-{rule_id}".encode()).hexdigest()
                    
                    if not await self._is_duplicate(h_str):
                        if (
                            self.mongo_client is not None
                            and self.mongo_client.db is not None
                        ):
                            try:
                                await insert_wazuh_logon_if_applicable(
                                    self.mongo_client.db,
                                    payload,
                                )
                            except Exception as ex:
                                logger.error(
                                    "No se pudo persistir wazuh_logon: %s",
                                    ex,
                                )
                        evento = await self.normalizer.normalize(payload, "wazuh")
                        if evento:
                            await self.redis_bus.publish_event(
                                self.redis_bus.STREAM_RAW,
                                evento.to_redis_dict(),
                            )

                        await self._invalidate_identity_session_cache_if_needed(
                            payload,
                            str(agent_ip).strip(),
                        )

                        self._processed_count += 1
                        if self._processed_count % 1000 == 0:
                            logger.info(f"Parser Wazuh procesó {self._processed_count} eventos válidos")
                        
                # Retornamos rápido (< 200 ms exigencia)
                return JSONResponse(status_code=200, content={"status": "ok"})
                
            except Exception as e:
                logger.error(f"Error procesando payload de Wazuh: {e}")
                # Siempre retornar OK a Wazuh para que no sature su cola intentando retransmitir eventos fallidos
                return JSONResponse(status_code=200, content={"status": "error", "message": "ignored"})

    def _parse_line(self, raw_json: Dict[str, Any]) -> Optional[dict]:
        """
        Extrae datos seguros del webhook JSON asumiendo que campos pueden faltar.
        """
        rule = raw_json.get("rule", {})
        level = rule.get("level", 0)
        
        # Ignorar reglas muy bajas
        if int(level) < 3:
            return None
        
        # Mapear level a risk_score base
        risk_score = 0
        if 3 <= level <= 5:
            risk_score = 20
        elif 6 <= level <= 9:
            risk_score = 50
        elif 10 <= level <= 12:
            risk_score = 75
        elif level >= 13:
            risk_score = 90
            
        raw_json["mapped_risk_score"] = risk_score
        return raw_json

    async def _invalidate_identity_session_cache_if_needed(
        self,
        payload: Dict[str, Any],
        agent_ip: str,
    ) -> None:
        if not agent_ip or agent_ip.lower() in ("unknown", ""):
            return
        rule = payload.get("rule") or {}
        rid = str(rule.get("id", "")).strip()
        desc = (rule.get("description") or "").lower()
        logoffs = _logoff_rule_ids()
        try:
            if rid and rid in logon_rule_ids():
                await self.redis_bus.cache_delete(f"{SESSION_CACHE_PREFIX}{agent_ip}")
                return
            if logoffs:
                if rid in logoffs:
                    await self.redis_bus.cache_delete(f"{SESSION_CACHE_PREFIX}{agent_ip}")
                return
            if "4634" in desc:
                await self.redis_bus.cache_delete(f"{SESSION_CACHE_PREFIX}{agent_ip}")
        except Exception as ex:
            logger.warning("invalidate identity:session %s: %s", agent_ip, ex)

    async def _is_duplicate(self, h_str: str) -> bool:
        key = f"dedup:wazuh:{h_str}"
        if await self.redis_bus.cache_exists(key):
            return True
        await self.redis_bus.cache_set(key, {"v":1}, ttl=600)
        return False

    async def start(self) -> None:
        """
        Lanza el servidor HTTP asíncrono en segundo plano (corutina).
        uvicorn.Server.serve() es bloqueante de await, perfecto para gather().
        """
        logger.info(f"Iniciando Wazuh HTTP Webhook Parser en el puerto {self.port}")
        
        config = uvicorn.Config(app=self.app, host="0.0.0.0", port=self.port, log_level="warning")
        server = uvicorn.Server(config)
        
        try:
            await server.serve()
        except asyncio.CancelledError:
            logger.info("Cerrando Wazuh Webhook Parser")
        except Exception as e:
            logger.error(f"Fallo craso en servidor Webhook Wazuh: {e}")
