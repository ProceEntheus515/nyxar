import os
import time
import httpx
import asyncio
from typing import Optional
from api.models import Enrichment

from shared.logger import get_logger
from enricher.validators.external_response import (
    AbuseIPDBResponse,
    validate_external_response,
)

logger = get_logger("enricher.apis.abuseipdb")

class AbuseIPDB:
    BASE_URL = "https://api.abuseipdb.com/api/v2/check"
    
    def __init__(self):
        self.api_key = os.getenv("ABUSEIPDB_API_KEY")
        # Rate limit: 1000/día = ~1 req / 86 seg. Usamos semáforo y token bucket
        self._semaphore = asyncio.Semaphore(1)
        self._last_call = 0.0
        self._min_gap = 86.4
        self.headers = {
            "Accept": "application/json",
            "Key": self.api_key or ""
        }

    async def check_ip(self, ip: str) -> Optional[Enrichment]:
        if not self.api_key:
            return None # Skip sin error if no key
            
        # Rate limit check (Fail fast sin sleep)
        if self._semaphore.locked() or (time.time() - self._last_call) < self._min_gap:
            logger.warning("[ABUSEIPDB] Rate limit alcanzado o ejecución bloqueada. Saltando API.")
            return None
            
        async with self._semaphore:
            self._last_call = time.time()
            start_t = time.time()
            
            try:
                async with httpx.AsyncClient(timeout=10) as client:
                    resp = await client.get(
                        self.BASE_URL,
                        params={"ipAddress": ip, "maxAgeInDays": "30", "verbose": "true"},
                        headers=self.headers
                    )
                    
                    latencia = round((time.time() - start_t) * 1000, 2)
                    
                    if resp.status_code == 429:
                        logger.warning(f"[ABUSEIPDB] HTTP 429 Too Many Requests (latencia {latencia}ms)")
                        return None
                        
                    resp.raise_for_status()
                    raw = resp.json().get("data") or {}
                    if not isinstance(raw, dict):
                        logger.warning("[ABUSEIPDB] Campo data no es objeto; se ignora.")
                        return None

                    validated = validate_external_response(
                        raw, AbuseIPDBResponse, "AbuseIPDB"
                    )
                    if validated is None:
                        return None

                    score = validated.abuseConfidenceScore
                    if score > 50:
                        rep = "malicioso"
                    elif score > 20:
                        rep = "sospechoso"
                    elif score == 0:
                        rep = "limpio"
                    else:
                        rep = "desconocido"
                        
                    logger.info(f"[API_CALL] API: AbuseIPDB | Valor: {ip} | Latencia: {latencia}ms | Status: {resp.status_code} | Res: {rep}")
                    
                    return Enrichment(
                        reputacion=rep, # type: ignore
                        fuente="AbuseIPDB",
                        pais_origen=validated.countryCode,
                        asn=validated.isp,
                    )
            except Exception as e:
                latencia = round((time.time() - start_t) * 1000, 2)
                logger.error(f"[API_CALL] API: AbuseIPDB | Valor: {ip} | Latencia: {latencia}ms | Error: {e}")
                return None
