"""
Script de verificación I10: MISP connector → Redis blocklists / misp:meta → Enricher.
Uso (PowerShell): python scripts/verify_misp_integration.py
Requiere Redis (REDIS_URL o redis://localhost:6379 por defecto).
Usa SCAN (scan_iter) en lugar de KEYS para no bloquear Redis en producción.
"""

from __future__ import annotations

import asyncio
import os
import sys

import redis.asyncio as aioredis


async def _count_scan(r: aioredis.Redis, pattern: str) -> int:
    n = 0
    async for _ in r.scan_iter(match=pattern, count=500):
        n += 1
    return n


async def main() -> None:
    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379")
    r = aioredis.from_url(redis_url, decode_responses=True)

    print("=== Verificando MISP Integration (I10) ===\n")

    misp_lists = [
        "blocklist:misp_ips",
        "blocklist:misp_domains",
        "blocklist:misp_hashes",
        "blocklist:misp_urls",
    ]

    try:
        for lista in misp_lists:
            size = await r.scard(lista)
            print(f"  {lista}: {size} IOCs")

        total = 0
        for lista in misp_lists:
            total += await r.scard(lista)

        if total == 0:
            print("\n[WARN] No hay IOCs de MISP en Redis")
            print("       Revisar MISP_URL, MISP_API_KEY y que misp_connector esté en ejecución")
        else:
            print(f"\n[OK] Total IOCs de MISP en blocklists: {total}")

        meta_n = await _count_scan(r, "misp:meta:*")
        print(f"[OK] Claves de metadata misp:meta:* (aprox. vía SCAN): {meta_n}")
    except Exception as e:
        print(f"[FAIL] Error consultando Redis: {e}", file=sys.stderr)
        raise
    finally:
        await r.aclose()

    print("\n=== Verificación I10 completada ===")


if __name__ == "__main__":
    asyncio.run(main())
