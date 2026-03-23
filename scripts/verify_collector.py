"""
Script de verificación: Collector → Redis (contrato I01, stream events:raw).
Uso: python scripts/verify_collector.py
Requiere Redis accesible (p. ej. docker-compose --profile lab up).
"""

from __future__ import annotations

import asyncio
import json
import os
import sys

import redis.asyncio as aioredis


def _data_field(entry: dict) -> str | None:
    """Obtiene el JSON del campo data con clave str o bytes según el cliente."""
    if not entry:
        return None
    raw = entry.get("data") if "data" in entry else entry.get(b"data")
    if raw is None:
        return None
    if isinstance(raw, bytes):
        return raw.decode("utf-8", errors="replace")
    return str(raw)


async def main() -> None:
    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379")
    r = aioredis.from_url(redis_url, decode_responses=True)

    print("=== Verificando Collector → Redis ===\n")

    messages = await r.xrevrange("events:raw", max="+", min="-", count=10)

    if not messages:
        print("[FAIL] No hay mensajes en events:raw")
        print("       Verificar que el collector y el simulador estén corriendo")
        await r.aclose()
        sys.exit(1)

    print(f"[OK] {len(messages)} mensajes encontrados en events:raw\n")

    latest_id, latest_data = messages[0]
    event_str = _data_field(latest_data)
    if not event_str:
        print("[FAIL] El último mensaje no tiene campo 'data' válido")
        await r.aclose()
        sys.exit(1)

    event = json.loads(event_str)

    required_fields = ["id", "timestamp", "source", "tipo", "interno", "externo"]
    missing = [f for f in required_fields if f not in event]
    if missing:
        print(f"[FAIL] Faltan campos requeridos: {missing}")
        await r.aclose()
        sys.exit(1)

    print(f"[OK] Formato correcto. Campos presentes: {list(event.keys())}")
    print(f"  - source: {event['source']}")
    print(f"  - tipo: {event['tipo']}")
    print(f"  - interno.usuario: {event['interno'].get('usuario', 'N/A')}")
    print(f"  - externo.valor: {event['externo'].get('valor', 'N/A')}")
    enr = event.get("enrichment")
    print(f"  - enrichment: {'presente' if enr else 'null (esperado en raw)'}")
    rs = event.get("risk_score")
    print(f"  - risk_score: {rs if rs is not None else 'null (esperado en raw)'}")

    sources: set[str] = set()
    for _msg_id, msg_data in messages:
        raw = _data_field(msg_data)
        if not raw:
            continue
        try:
            ev = json.loads(raw)
            sources.add(str(ev.get("source", "unknown")))
        except json.JSONDecodeError:
            continue

    print(f"\n[OK] Fuentes detectadas: {sources}")

    if len(sources) >= 2:
        print("[OK] Múltiples fuentes activas — collector funcionando correctamente")
    else:
        print("[WARN] Solo una fuente activa — verificar que todos los parsers estén corriendo")

    await r.aclose()
    print("\n=== Verificación I01 COMPLETADA ===")


if __name__ == "__main__":
    asyncio.run(main())
