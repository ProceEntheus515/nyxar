"""
Script de verificación: pipeline Enricher (I02).
Uso: python scripts/verify_enricher.py
Requiere collector + enricher activos y tráfico en events:raw.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys

import redis.asyncio as aioredis


def _data_field(msg_data: dict) -> str | None:
    if not msg_data:
        return None
    raw = msg_data.get("data") if "data" in msg_data else msg_data.get(b"data")
    if raw is None:
        return None
    if isinstance(raw, bytes):
        return raw.decode("utf-8", errors="replace")
    return str(raw)


def _group_name(entry: dict) -> str:
    n = entry.get("name")
    if isinstance(n, bytes):
        return n.decode("utf-8", errors="replace")
    return str(n or "")


async def main() -> None:
    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379")
    r = aioredis.from_url(redis_url, decode_responses=True)

    print("=== Verificando Enricher ===\n")

    enriched_len = await r.xlen("events:enriched")
    if enriched_len == 0:
        print("[WARN] events:enriched está vacío — esperando 5 segundos...")
        await asyncio.sleep(5)
        enriched_len = await r.xlen("events:enriched")

    if enriched_len == 0:
        print("[FAIL] events:enriched sigue vacío.")
        print("       Verificar que el enricher esté corriendo y consumiendo de events:raw")
        await r.aclose()
        sys.exit(1)

    print(f"[OK] {enriched_len} mensajes en events:enriched")

    messages = await r.xrevrange("events:enriched", max="+", min="-", count=20)

    with_enrichment = 0
    with_risk_score = 0
    reputations: dict[str, int] = {}

    for _msg_id, msg_data in messages:
        raw = _data_field(msg_data)
        if not raw:
            continue
        try:
            ev = json.loads(raw)
        except json.JSONDecodeError:
            continue

        enr = ev.get("enrichment")
        if enr is not None:
            with_enrichment += 1
            rep = str(enr.get("reputacion", "desconocido"))
            reputations[rep] = reputations.get(rep, 0) + 1

        rs = ev.get("risk_score")
        if rs is not None and isinstance(rs, (int, float)):
            if 0 <= int(rs) <= 100:
                with_risk_score += 1

    n = len(messages)
    print(f"[OK] {with_enrichment}/{n} eventos tienen enrichment completo")
    print(f"[OK] {with_risk_score}/{n} eventos tienen risk_score en rango 0-100")
    print(f"  Distribución de reputaciones: {reputations}")

    groups = await r.xinfo_groups("events:raw")
    enricher_group = None
    for g in groups:
        if _group_name(g) == "enricher-group":
            enricher_group = g
            break

    if not enricher_group:
        print("[FAIL] consumer group 'enricher-group' no existe en events:raw")
        await r.aclose()
        sys.exit(1)

    pending = enricher_group.get("pending", 0)
    print(f"\n[OK] Consumer group 'enricher-group' existe")
    print(f"  - Mensajes pendientes sin ACK: {pending}")
    if pending > 100:
        print("  [WARN] Muchos mensajes pendientes — el enricher puede estar lento")

    raw_messages = await r.xrevrange("events:raw", max="+", min="-", count=1)
    enriched_messages = await r.xrevrange("events:enriched", max="+", min="-", count=1)

    if raw_messages and enriched_messages:
        raw_id = str(raw_messages[0][0])
        enriched_id = str(enriched_messages[0][0])
        try:
            raw_ms = int(raw_id.split("-")[0])
            enriched_ms = int(enriched_id.split("-")[0])
            latency_ms = enriched_ms - raw_ms
            print(f"\n[OK] Delta aproximado entre últimos IDs raw/enriched: {latency_ms} ms")
            if latency_ms > 2000:
                print("  [WARN] Delta alto — revisar APIs externas o caché")
        except (ValueError, IndexError):
            print("\n[WARN] No se pudo calcular latencia a partir de IDs de stream")

    await r.aclose()
    print("\n=== Verificación I02 COMPLETADA ===")


if __name__ == "__main__":
    asyncio.run(main())
