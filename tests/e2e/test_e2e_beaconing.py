"""
E2E: Detección de Beaconing (C2 Periodic Callback)

Escenario: Un host interno consulta el mismo dominio externo cada exactamente
5 minutos durante 50+ minutos (patrón de beaconing clásico).

El correlator debe detectar este patrón y generar un incidente de alta/crítica severidad.
"""

import pytest
import asyncio
import time
from datetime import datetime, timezone, timedelta

from tests.e2e.conftest_e2e import (
    publish_raw_event, wait_for_incident, count_incidents,
    get_identity_risk_score, MONGO_DB
)

pytestmark = [pytest.mark.e2e, pytest.mark.asyncio]

BEACONING_DOMAIN  = "c2-beacon-test-9f7a.xyz"
TARGET_IDENTITY   = "ventas.garcia"
TARGET_IP         = "192.168.10.42"
DELAY_BETWEEN     = 5  # segundos entre peticiones (en test, no minutos reales)
BEACON_COUNT      = 10


def _make_dns_event(ts_offset_secs: int = 0) -> dict:
    """Genera un evento DNS con timestamp controlado."""
    ts = (datetime.now(timezone.utc) + timedelta(seconds=ts_offset_secs)).isoformat()
    return {
        "source": "dns",
        "tipo": "query",
        "timestamp": ts,
        "interno": {
            "ip": TARGET_IP,
            "hostname": "ventas-garcia-pc",
            "usuario": TARGET_IDENTITY,
            "area": "Ventas"
        },
        "externo": {
            "valor": BEACONING_DOMAIN,
            "tipo": "dominio"
        },
        "detalles": {"query_type": "A"}
    }


@pytest.mark.timeout(180)
async def test_beaconing_detectado(full_stack, clean_state):
    """
    1. Inyectar 10 consultas al mismo dominio con intervalos regulares exactos.
    2. Esperar hasta 120s para que el correlator detecte el patrón.
    3. Verificar incidente en MongoDB con severidad alta/critica.
    4. Verificar risk_score de la identidad > 60.
    """
    redis_url = full_stack["redis_url"]
    mongo_url = full_stack["mongo_url"]

    # Inyectar eventos con timestamps escalonados exactos (simulando 5min intervals)
    # El correlator analiza por ventana temporal — usamos timestamps ficticios espaciados
    for i in range(BEACON_COUNT):
        # Timestamps espaciados en el pasado: simula 10 beacons en las últimas ~50min
        offset_secs = -(BEACON_COUNT - i) * 300  # 300s = 5min
        event = _make_dns_event(ts_offset_secs=offset_secs)
        await publish_raw_event(redis_url, event)
        await asyncio.sleep(0.05)  # Pequeña pausa para no saturar el stream

    # Esperar que el correlator procese y genere el incidente
    incident = await wait_for_incident(
        mongo_url=mongo_url,
        db_name=MONGO_DB,
        filter_query={
            "$or": [
                {"titulo": {"$regex": "beaconing", "$options": "i"}},
                {"titulo": {"$regex": "C2",         "$options": "i"}},
                {"titulo": {"$regex": "beacon",     "$options": "i"}},
            ],
            "host_afectado": {"$regex": TARGET_IDENTITY, "$options": "i"},
        },
        timeout_secs=120
    )

    assert incident is not None, (
        f"El correlator NO detectó el beaconing hacia {BEACONING_DOMAIN} "
        f"en 120 segundos. Revisar reglas del correlator."
    )
    assert incident.get("severidad") in ("alta", "critica"), (
        f"Severidad esperada alta/critica, obtenida: {incident.get('severidad')}"
    )

    # Verificar risk_score actualizado
    score = await get_identity_risk_score(mongo_url, MONGO_DB, TARGET_IDENTITY)
    assert score > 60, (
        f"Risk score de {TARGET_IDENTITY} debería ser >60 tras beaconing. "
        f"Obtenido: {score}"
    )


@pytest.mark.timeout(90)
async def test_beaconing_no_dispara_con_intervalos_irregulares(full_stack, clean_state):
    """
    5 consultas al mismo dominio con intervalos IRREGULARES → NO debe generar incidente.
    Simula navegación normal de usuario (no beaconing).
    """
    redis_url = full_stack["redis_url"]
    mongo_url = full_stack["mongo_url"]

    # Intervalos irregulares (minutos: 2, 7, 1, 15) — no periódicos
    offsets_min = [-30, -28, -21, -20, -5]
    for offset_min in offsets_min:
        event = _make_dns_event(ts_offset_secs=offset_min * 60)
        event["externo"]["valor"] = "trafico-normal-irregular.com"
        await publish_raw_event(redis_url, event)
        await asyncio.sleep(0.05)

    # Esperar 60s y verificar que NO se creó un incidente de beaconing
    await asyncio.sleep(60)

    count = await count_incidents(
        mongo_url=mongo_url,
        db_name=MONGO_DB,
        filter_query={
            "$or": [
                {"titulo": {"$regex": "beaconing",  "$options": "i"}},
                {"titulo": {"$regex": "beacon",     "$options": "i"}},
            ],
            "host_afectado": {"$regex": TARGET_IDENTITY, "$options": "i"},
        }
    )

    assert count == 0, (
        f"Falso positivo: el correlator generó {count} incidente(s) de beaconing "
        f"para tráfico con intervalos irregulares (navegación normal)."
    )
