"""
Fixtures compartidas para tests End-to-End de NYXAR.

Estos tests requieren el stack completo corriendo (Redis + MongoDB + todos los servicios).
Correr con:
    pytest tests/e2e/ -v -m e2e --asyncio-mode=auto

Para levantar el stack antes de correr:
    docker-compose --profile lab up -d
    pytest tests/e2e/ -v -m e2e --asyncio-mode=auto
"""

import asyncio
import subprocess
import time
import pytest
import redis.asyncio as aioredis
import motor.motor_asyncio

from shared.logger import get_logger

logger = get_logger("tests.e2e")

REDIS_URL = "redis://localhost:6379"
MONGO_URL = "mongodb://localhost:27017"
MONGO_DB   = "nyxar"
API_BASE   = "http://localhost:8000"

# --- Constantes de timing e2e ---
MAX_DETECTION_WAIT_SECS = 120    # Timeout máximo esperando un incidente
POLL_INTERVAL_SECS      = 2      # Intervalo entre chequeos
API_BOOT_WAIT_SECS      = 5      # Espera inicial al levantar stack

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def wait_for_redis(url: str, retries: int = 20, delay: float = 1.0):
    for _ in range(retries):
        try:
            r = aioredis.from_url(url)
            await r.ping()
            await r.aclose()
            return True
        except Exception:
            await asyncio.sleep(delay)
    return False


async def wait_for_mongo(url: str, retries: int = 20, delay: float = 1.0):
    for _ in range(retries):
        try:
            client = motor.motor_asyncio.AsyncIOMotorClient(url, serverSelectionTimeoutMS=2000)
            await client.admin.command("ping")
            client.close()
            return True
        except Exception:
            await asyncio.sleep(delay)
    return False


# ---------------------------------------------------------------------------
# Fixtures de sesión
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def event_loop():
    """Shared event loop for all e2e session fixtures."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def full_stack(event_loop):
    """
    Levanta el stack completo via docker-compose --profile lab.
    Espera que Redis y MongoDB estén healthy antes de ceder el fixture.
    Al finalizar la sesión limpia todos los datos de test.
    """
    logger.info("[E2E] Levantando docker-compose --profile lab...")
    proc = subprocess.run(
        ["docker-compose", "--profile", "lab", "up", "-d"],
        capture_output=True,
        text=True,
        cwd="."
    )
    if proc.returncode != 0:
        pytest.fail(f"docker-compose up falló:\n{proc.stderr}")

    # Esperar servicios core
    redis_ok = await wait_for_redis(REDIS_URL)
    mongo_ok = await wait_for_mongo(MONGO_URL)

    if not redis_ok:
        pytest.fail("Redis no respondió en tiempo. Abort e2e.")
    if not mongo_ok:
        pytest.fail("MongoDB no respondió en tiempo. Abort e2e.")

    await asyncio.sleep(API_BOOT_WAIT_SECS)  # Dejar que API y correlator terminen de iniciar
    logger.info("[E2E] Stack listo. Corriendo tests.")

    yield {
        "redis_url": REDIS_URL,
        "mongo_url": MONGO_URL,
        "api_base":  API_BASE,
    }

    # Teardown de sesión: bajar servicios y eliminar datos de laboratorio
    logger.info("[E2E] Teardown: limpiando datos de la sesión e2e...")
    subprocess.run(
        ["docker-compose", "--profile", "lab", "down", "--volumes"],
        capture_output=True,
        cwd="."
    )


@pytest.fixture
async def clean_state(full_stack):
    """
    Limpia Redis y MongoDB antes de cada test e2e para garantizar aislamiento.
    Solo elimina colecciones de datos operativos (no configuración).
    """
    r = aioredis.from_url(full_stack["redis_url"])

    # Limpiar streams y claves de trabajo (prefijos conocidos del sistema)
    patterns = [
        "events:*", "identities:*", "enricher:*",
        "correlator:*", "blocklist:*", "parser:*"
    ]
    for pattern in patterns:
        cursor = b"0"
        while True:
            cursor, keys = await r.scan(cursor=cursor, match=pattern, count=500)
            if keys:
                await r.delete(*keys)
            if cursor == b"0":
                break

    await r.aclose()

    # Limpiar MongoDB
    mongo = motor.motor_asyncio.AsyncIOMotorClient(full_stack["mongo_url"])
    db = mongo[MONGO_DB]
    for col in ["events", "incidents", "identities", "honeypot_hits", "ai_memos"]:
        await db[col].delete_many({})
    mongo.close()

    yield

    # Post-test: nada que hacer (el siguiente test también limpiará)


# ---------------------------------------------------------------------------
# Helpers reutilizables en los tests
# ---------------------------------------------------------------------------

async def publish_raw_event(redis_url: str, event: dict) -> None:
    """Publica en events:raw con el mismo envelope que RedisBus.publish_event (campo data JSON)."""
    import json

    from api.models import Evento

    allowed = (
        "id",
        "timestamp",
        "source",
        "tipo",
        "interno",
        "externo",
        "enrichment",
        "risk_score",
        "correlaciones",
    )
    payload = {k: event[k] for k in allowed if k in event}
    evento = Evento(**payload)
    r = aioredis.from_url(redis_url, decode_responses=True)
    await r.xadd("events:raw", {"data": json.dumps(evento.to_redis_dict())})
    await r.aclose()


async def wait_for_incident(
    mongo_url: str,
    db_name: str,
    filter_query: dict,
    timeout_secs: int = MAX_DETECTION_WAIT_SECS,
    poll_secs: float = POLL_INTERVAL_SECS
):
    """
    Hace polling en MongoDB hasta encontrar un incidente que matchea filter_query
    o expira el timeout. Retorna el documento encontrado o None.
    """
    mongo = motor.motor_asyncio.AsyncIOMotorClient(mongo_url)
    db = mongo[db_name]
    start = time.time()
    while True:
        elapsed = time.time() - start
        if elapsed > timeout_secs:
            mongo.close()
            return None
        doc = await db.incidents.find_one(filter_query)
        if doc:
            mongo.close()
            return doc
        await asyncio.sleep(poll_secs)


async def get_identity_risk_score(mongo_url: str, db_name: str, identidad_id: str) -> int:
    """Lee el risk_score actual de una identidad desde MongoDB."""
    mongo = motor.motor_asyncio.AsyncIOMotorClient(mongo_url)
    doc = await mongo[db_name].identities.find_one({"id": identidad_id})
    mongo.close()
    return doc.get("risk_score_actual", 0) if doc else 0


async def count_incidents(mongo_url: str, db_name: str, filter_query: dict) -> int:
    """Cuenta incidentes que matchean el filtro dado."""
    mongo = motor.motor_asyncio.AsyncIOMotorClient(mongo_url)
    count = await mongo[db_name].incidents.count_documents(filter_query)
    mongo.close()
    return count
