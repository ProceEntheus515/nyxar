import os
import time
import httpx
import asyncio
from typing import Optional
from api.models import Enrichment

from shared.logger import get_logger

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
                            detalles={"pulse_count": 0}
                        )
                        
                    resp.raise_for_status()
                    data = resp.json()
                    
                    pulse_count = data.get("pulse_info", {}).get("count", 0)
                    pulses = data.get("pulse_info", {}).get("pulses", [])
                    
                    tags = []
                    for p in pulses:
                        tags.extend(p.get("tags", []))
                    tags = list(set(tags)) # Deduplicate
                    
                    if pulse_count > 0:
                        rep = "sospechoso"
                        if pulse_count > 3 or any(t.lower() in ['malware', 'phishing', 'c2', 'ransomware'] for t in tags):
                            rep = "malicioso"
                    else:
                        rep = "limpio"
                        
                    logger.info(f"[API_CALL] API: OTX | Valor: {valor} | Latencia: {latencia}ms | Status: {resp.status_code} | Res: {rep}")
                    
                    return Enrichment(
                        reputacion=rep, # type: ignore
                        fuente="AlienVault OTX",
                        detalles={
                            "pulse_count": pulse_count,
                            "country": data.get("base_indicator", {}).get("country_name", ""),
                            "asn": data.get("asn", ""),
                            "tags": tags[:10] # Top 10 tags max
                        }
                    )
            except Exception as e:
                latencia = round((time.time() - start_t) * 1000, 2)
                logger.error(f"[API_CALL] API: OTX | Valor: {valor} | Latencia: {latencia}ms | Error: {e}")
                return None
