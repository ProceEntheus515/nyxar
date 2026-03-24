"""
Verificación I12: colección response_proposals, API GET /response/proposals y Redis accesible.
Uso: python scripts/verify_response_flow.py
Variables: MONGO_URL o MONGODB_URL, REDIS_URL, API_BASE (default http://localhost:8000/api/v1).
Opcional: NYXAR_ACCESS_TOKEN (JWT de POST /api/v1/auth/login) para GET /response/proposals.
"""

from __future__ import annotations

import asyncio
import os
import sys

import httpx
import redis.asyncio as aioredis
from motor.motor_asyncio import AsyncIOMotorClient


async def main() -> None:
    mongo_url = os.environ.get("MONGO_URL") or os.environ.get(
        "MONGODB_URL",
        "mongodb://localhost:27017/nyxar",
    )
    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379")
    api_base = os.environ.get("API_BASE", "http://localhost:8000/api/v1").rstrip("/")

    print("=== Verificando Auto Response Flow (I12) ===\n")

    mongo = AsyncIOMotorClient(mongo_url)
    db = mongo.get_default_database()
    r = aioredis.from_url(redis_url, decode_responses=True)

    try:
        names = await db.list_collection_names()
        if "response_proposals" not in names:
            print("[WARN] Coleccion response_proposals no existe aun")
            print("       Comprobar auto_response y que se haya generado al menos una propuesta")
        else:
            total = await db.response_proposals.count_documents({})
            pending = await db.response_proposals.count_documents(
                {"estado": "pendiente_aprobacion"},
            )
            print(f"[OK] response_proposals: {total} total, {pending} pendiente_aprobacion")

        try:
            pong = await r.ping()
            print(f"[OK] Redis PING: {pong}")
        except Exception as e:
            print(f"[WARN] Redis: {e}")

        url = f"{api_base}/response/proposals"
        token = (os.environ.get("NYXAR_ACCESS_TOKEN") or "").strip()
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        async with httpx.AsyncClient(timeout=15.0, headers=headers) as client:
            try:
                resp = await client.get(url)
                if resp.status_code == 200:
                    body = resp.json()
                    total_api = body.get("total", "?")
                    print(f"[OK] GET {url} -> total={total_api}")
                else:
                    print(f"[FAIL] GET {url} HTTP {resp.status_code}: {resp.text[:200]}")
            except httpx.ConnectError:
                print(f"[WARN] API no alcanzable en {api_base} (levantar FastAPI)")
            except Exception as e:
                print(f"[FAIL] GET proposals: {e}")
    finally:
        await r.aclose()
        mongo.close()

    print("\n=== Verificacion I12 completada ===")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(130)
