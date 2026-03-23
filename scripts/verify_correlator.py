"""
Script de verificación: Correlator (I03).
Uso: python scripts/verify_correlator.py
"""

from __future__ import annotations

import asyncio
import json
import os
import sys

import redis.asyncio as aioredis
from motor.motor_asyncio import AsyncIOMotorClient


def _group_name(entry: dict) -> str:
    n = entry.get("name")
    if isinstance(n, bytes):
        return n.decode("utf-8", errors="replace")
    return str(n or "")


def _mongo_db_name() -> str:
    return os.environ.get("MONGO_DB", "nyxar")


async def main() -> None:
    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379")
    mongo_url = (
        os.environ.get("MONGODB_URL")
        or os.environ.get("MONGO_URL")
        or "mongodb://localhost:27017"
    )
    db_name = _mongo_db_name()

    r = aioredis.from_url(redis_url, decode_responses=True)
    mongo = AsyncIOMotorClient(mongo_url)
    db = mongo[db_name]

    print("=== Verificando Correlator ===\n")

    groups = await r.xinfo_groups("events:enriched")
    correlator_group = next(
        (g for g in groups if _group_name(g) == "correlator-group"),
        None,
    )

    if not correlator_group:
        print("[FAIL] consumer group 'correlator-group' no existe en events:enriched")
        mongo.close()
        await r.aclose()
        sys.exit(1)

    print("[OK] Consumer group 'correlator-group' activo")
    print(f"  Pending: {correlator_group.get('pending', 0)} mensajes")

    identity_count = await db.identities.count_documents({})
    print(f"\n[OK] {identity_count} documentos en colección identities")

    if identity_count == 0:
        print("[WARN] No hay identidades — el correlator puede no estar actualizando aún")
    else:
        sample = await db.identities.find_one(
            {},
            projection={"id": 1, "risk_score": 1, "risk_score_actual": 1, "area": 1},
        )
        if sample:
            sid = sample.get("id", "N/A")
            score = sample.get("risk_score_actual", sample.get("risk_score", "N/A"))
            print(f"  Ejemplo: {sid} — score: {score}")

    incident_count = await db.incidents.count_documents({})
    print(f"\n[OK] {incident_count} incidentes en MongoDB")
    if incident_count > 0:
        latest = await db.incidents.find_one({}, sort=[("created_at", -1)])
        if not latest:
            latest = await db.incidents.find_one({}, sort=[("timestamp", -1)])
        if latest:
            titulo = latest.get("titulo") or latest.get("patron") or "N/A"
            sev = latest.get("severidad", "N/A")
            print(f"  Último: {titulo} — {sev}")

    print("\nVerificando PubSub canal 'dashboard:alerts'...")
    pubsub = r.pubsub()
    await pubsub.subscribe("dashboard:alerts")

    test_payload = json.dumps({"tipo": "test", "data": {"msg": "verify_correlator"}})
    await r.publish("dashboard:alerts", test_payload)

    received_ok = False
    for _ in range(50):
        await asyncio.sleep(0.05)
        msg = await pubsub.get_message(ignore_subscribe_messages=True)
        if not msg or msg.get("type") != "message":
            continue
        raw = msg.get("data")
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8", errors="replace")
        try:
            received = json.loads(raw)
            if received.get("tipo") == "test":
                received_ok = True
                break
        except json.JSONDecodeError:
            continue

    if received_ok:
        print("[OK] PubSub 'dashboard:alerts' funcionando correctamente")
    else:
        print("[WARN] No se recibió el mensaje de prueba en PubSub a tiempo")
        print("       Verificar Redis y que no haya otro cliente saturando el canal")

    await pubsub.unsubscribe("dashboard:alerts")
    await pubsub.aclose()
    mongo.close()
    await r.aclose()
    print("\n=== Verificación I03 COMPLETADA ===")


if __name__ == "__main__":
    asyncio.run(main())
