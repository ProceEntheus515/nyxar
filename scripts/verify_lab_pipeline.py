"""
Verificacion I16: inyecta un evento en events:raw (mismo envelope que RedisBus.publish_event)
y comprueba presencia en events:enriched. Mongo events es opcional si no hay writer en el pipeline.
Uso: python scripts/verify_lab_pipeline.py
Variables: REDIS_URL, MONGO_URL o MONGODB_URL
Requiere enricher activo consumiendo events:raw (grupo enricher-group).
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
import uuid
from datetime import datetime, timezone

import redis.asyncio as aioredis
from motor.motor_asyncio import AsyncIOMotorClient

# Raiz del repo para importar api.models
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from api.models import Evento  # noqa: E402


async def main() -> None:
    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379")
    mongo_url = os.environ.get("MONGO_URL") or os.environ.get(
        "MONGODB_URL",
        "mongodb://localhost:27017/nyxar",
    )

    print("=== Verificando pipeline lab (I16) ===\n")

    r = aioredis.from_url(redis_url, decode_responses=True)
    mongo = AsyncIOMotorClient(mongo_url)
    db = mongo.get_default_database()

    test_id = f"evt_test_{int(time.time())}_{uuid.uuid4().hex[:4]}"
    test_domain = f"verify-{uuid.uuid4().hex[:8]}.test.com"

    test_evento = Evento(
        id=test_id,
        timestamp=datetime.now(timezone.utc),
        source="dns",
        tipo="query",
        interno={
            "ip": "192.168.1.45",
            "hostname": "PC-TEST-01",
            "usuario": "test.verify",
            "area": "testing",
        },
        externo={"valor": test_domain, "tipo": "dominio"},
        enrichment=None,
        risk_score=None,
        correlaciones=[],
    )
    payload = test_evento.to_redis_dict()

    try:
        try:
            await r.ping()
        except Exception as e:
            print(f"[FAIL] Redis no alcanzable ({redis_url}): {e}")
            return

        await r.xadd("events:raw", {"data": json.dumps(payload)})
        print(f"[OK] Paso 1: evento publicado en events:raw (id={test_id})")
        print("     Esperando al enricher (hasta ~15s)...")

        found_enriched = False
        for _ in range(30):
            await asyncio.sleep(0.5)
            enriched_msgs = await r.xrevrange("events:enriched", max="+", min="-", count=40)
            for _msg_id, msg_data in enriched_msgs:
                raw = msg_data.get("data")
                if not raw:
                    continue
                try:
                    ev = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                if ev.get("id") == test_id:
                    found_enriched = True
                    enr = ev.get("enrichment") or {}
                    rep = enr.get("reputacion", "none")
                    print("[OK] Paso 2: evento encontrado en events:enriched")
                    print(f"     enrichment.reputacion: {rep}")
                    print(f"     risk_score: {ev.get('risk_score')}")
                    break
            if found_enriched:
                break

        if not found_enriched:
            print("[FAIL] Paso 2: evento no aparece en events:enriched")
            print("       Comprobar enricher y grupo enricher-group en events:raw")

        await asyncio.sleep(1)
        mongo_event = await db.events.find_one({"id": test_id})
        if mongo_event:
            print("[OK] Paso 3: evento persistido en MongoDB (coleccion events)")
        else:
            print("[WARN] Paso 3: no hay documento en events con este id")
            print("       En este repo el enricher no escribe events; es esperable sin otro servicio")

        if found_enriched:
            print("\n[OK] Pipeline raw -> enriched operativo")
        else:
            print("\n[FAIL] Pipeline roto o enricher no consumiendo")

    finally:
        await r.aclose()
        mongo.close()

    print("\n=== Verificacion I16 completada ===")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(130)
