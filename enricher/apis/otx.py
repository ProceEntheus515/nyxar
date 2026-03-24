import os
import time
import httpx
import asyncio
from typing import Optional, Any
from api.models import Enrichment

from shared.logger import get_logger
from enricher.validators.external_response import (
    OTXGeneralResponse,
    validate_external_response,
)

logger = get_logger("enricher.apis.otx")

class AlienVaultOTX:
    BASE_URL = "https://otx.alienvault.com/api/v1/indicators"
    
    def __init__(self):
        self.api_key = os.getenv("OTX_API_KEY")
        # Rate limit: 10 req / sec. Pool dimensionado con Semáforo.
        self._semaphore = asyncio.Semaphore(10)
        self.headers = {
            "Accept": "application/json",
            "X-OTX-API-KEY": self.api_key or ""
        }

    async def check_indicator(self, valor: str, tipo: str) -> Optional[Enrichment]:
        if not self.api_key:
            return None # Salto
            
        endpoint = ""
        if tipo == "dominio":
            endpoint = f"/domain/{valor}/general"
        elif tipo == "ip":
            endpoint = f"/IPv4/{valor}/general"
        else:
            return None

        # Try-acquire para no bloquear a la app entera si superan pico de 10 requests sin control upstream.
        if self._semaphore.locked():
            logger.warning(f"[OTX] Rate limit/semáforo bloqueado ({self._semaphore._value}). Saltando.")
            return None
            
        async with self._semaphore:
            start_t = time.time()
            try:
                # OTX Rate Limit: delay implícito asegurado por semaforo local + latencia no ahoga sus endps.
                async with httpx.AsyncClient(timeout=10) as client:
                    resp = await client.get(
                        f"{self.BASE_URL}{endpoint}",
                        headers=self.headers
                    )
                    
                    latencia = round((time.time() - start_t) * 1000, 2)
                    
                    if resp.status_code == 429:
                        logger.warning(f"[OTX] HTTP 429 Rate Limit. Latencia {latencia}ms")
                        return None
                        
                    if resp.status_code == 404:
                        return Enrichment(
                            reputacion="desconocido", # type: ignore
                            fuente="AlienVault OTX",
                        )
                        
                    resp.raise_for_status()
                    raw = resp.json()
                    if not isinstance(raw, dict):
                        logger.warning("[OTX] Cuerpo JSON no es objeto; se ignora.")
                        return None

                    validated = validate_external_response(
                        raw, OTXGeneralResponse, "AlienVault OTX"
                    )
                    if validated is None:
                        return None

                    pi = validated.pulse_info
                    pulse_count = pi.count if pi else 0
                    pulses: list[Any] = pi.pulses if pi else []
                    
                    tags = []
                    for p in pulses:
                        if isinstance(p, dict):
                            tags.extend(p.get("tags", []))
                    tags = list(set(tags)) # Deduplicate
                    
                    if pulse_count > 0:
                        rep = "sospechoso"
                        if pulse_count > 3 or any(t.lower() in ['malware', 'phishing', 'c2', 'ransomware'] for t in tags):
                            rep = "malicioso"
                    else:
                        rep = "limpio"
                        
                    logger.info(f"[API_CALL] API: OTX | Valor: {valor} | Latencia: {latencia}ms | Status: {resp.status_code} | Res: {rep}")

                    base = validated.base_indicator or {}
                    country = ""
                    if isinstance(base, dict):
                        country = str(base.get("country_name") or "")
                    
                    return Enrichment(
                        reputacion=rep, # type: ignore
                        fuente="AlienVault OTX",
                        pais_origen=country or None,
                        asn=validated.asn,
                        tags=tags[:10],
                    )
            except Exception as e:
                latencia = round((time.time() - start_t) * 1000, 2)
                logger.error(f"[API_CALL] API: OTX | Valor: {valor} | Latencia: {latencia}ms | Error: {e}")
                return None
