"""
Verificacion I13: heartbeat del notifier en Redis, publicacion de prueba y traza en MongoDB.
Uso: python scripts/verify_notifier.py
Variables: REDIS_URL, MONGO_URL o MONGODB_URL (misma convencion que shared/mongo_client).
Requiere notifier en ejecucion para heartbeat y procesamiento del mensaje de prueba.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from datetime import datetime, timezone

import redis.asyncio as aioredis
from motor.motor_asyncio import AsyncIOMotorClient


async def main() -> None:
    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379")
    mongo_url = os.environ.get("MONGO_URL") or os.environ.get(
        "MONGODB_URL",
        "mongodb://localhost:27017/nyxar",
    )

    print("=== Verificando Notifier (I13) ===\n")

    r = aioredis.from_url(redis_url, decode_responses=True)
    mongo = AsyncIOMotorClient(mongo_url)
    db = mongo.get_default_database()

    try:
        raw_hb = await r.get("heartbeat:notifier")
        if raw_hb:
            try:
                data = json.loads(raw_hb) if isinstance(raw_hb, str) else raw_hb
                ts = data.get("ts") if isinstance(data, dict) else None
                print(f"[OK] Notifier heartbeat presente. ts={ts}")
            except json.JSONDecodeError:
                print(f"[WARN] heartbeat:notifier no es JSON valido: {raw_hb!r}")
        else:
            print("[WARN] Sin heartbeat:notifier (notifier no arrancado o Redis distinto)")
            print("       Arrancar: python -m notifier.main")

        before = datetime.now(timezone.utc).isoformat()

        test_notification = json.dumps(
            {
                "tipo": "test",
                "data": {
                    "severidad": "info",
                    "titulo": "Test de verificacion",
                    "mensaje": "Mensaje de integracion I13",
                },
            }
        )
        n = await r.publish("notifications:urgent", test_notification)
        print(f"[OK] Publicado en notifications:urgent (suscriptores conectados: {n})")

        await asyncio.sleep(2)

        recent = await db.notifications_log.find_one(
            {
                "ts": {"$gte": before},
                "evento_tipo": "notifications_urgent",
            },
            sort=[("ts", -1)],
        )
        if recent:
            print("[OK] Entrada reciente en notifications_log (notifications_urgent)")
        else:
            print("[WARN] No hay entrada nueva en notifications_log tras el test")
            print("       Posibles causas: notifier detenido, sin destinatarios NOTIFY_*,")
            print("       throttling/dedup, o Mongo distinto al del notifier")

        # Publica en dashboard:alerts con severidad MEDIA: el notifier debe suscribirse y filtrar
        # (no dispara process_event; evita emails/WhatsApp en entornos reales).
        dash_payload = json.dumps(
            {
                "tipo": "new_incident",
                "data": {
                    "id": "verify-notifier-dash",
                    "severidad": "MEDIA",
                    "patron": "verify_notifier",
                    "titulo": "Incidente de prueba I13",
                    "descripcion": "Solo comprobacion PubSub",
                },
            }
        )
        n2 = await r.publish("dashboard:alerts", dash_payload)
        print(
            f"[OK] Publicado en dashboard:alerts (suscriptores: {n2}; severidad MEDIA filtrada por motor)"
        )

    finally:
        await r.aclose()
        mongo.close()

    print("\n=== Verificacion I13 completada ===")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(130)
