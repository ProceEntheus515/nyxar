"""
E2E: Detección de Phishing Coordinado Multi-Víctima

Escenario: 3 usuarios del área de RRHH reciben el mismo dominio de phishing
en una ventana de 15 minutos. El correlator debe agruparlos en UN SOLO
incidente (no 3 separados) como campaña coordinada.
"""

import pytest
import asyncio
from datetime import datetime, timezone, timedelta

from tests.e2e.conftest_e2e import (
    publish_raw_event, wait_for_incident, count_incidents, MONGO_DB
)

pytestmark = [pytest.mark.e2e, pytest.mark.asyncio]

PHISHING_DOMAIN = "login-rrhh-verificacion-urgente.xyz"

# Las 3 víctimas del área RRHH
VICTIMS = [
    {"id": "rrhh.martinez", "ip": "192.168.20.11", "hostname": "rrhh-martinez-pc"},
    {"id": "rrhh.perez",    "ip": "192.168.20.12", "hostname": "rrhh-perez-pc"},
    {"id": "rrhh.gomez",    "ip": "192.168.20.13", "hostname": "rrhh-gomez-pc"},
]


def _make_phishing_event(victim: dict, ts_offset_secs: int = 0) -> dict:
    ts = (datetime.now(timezone.utc) + timedelta(seconds=ts_offset_secs)).isoformat()
    return {
        "source": "dns",
        "tipo": "query",
        "timestamp": ts,
        "interno": {
            "ip": victim["ip"],
            "hostname": victim["hostname"],
            "usuario": victim["id"],
            "area": "RRHH"
        },
        "externo": {
            "valor": PHISHING_DOMAIN,
            "tipo": "dominio"
        },
        "detalles": {"query_type": "A", "status": "NOERROR"}
    }


@pytest.mark.timeout(180)
async def test_phishing_correlacionado(full_stack, clean_state):
    """
    1. Inyectar phishing a 3 usuarios de RRHH simultáneamente.
    2. Verificar que se genera 1 solo incidente (agrupado) con las 3 referencias.
    3. El incidente debe listar los 3 usuarios como afectados.
    """
    redis_url = full_stack["redis_url"]
    mongo_url = full_stack["mongo_url"]

    # Inyectar los 3 eventos casi simultáneos (dentro de 2 minutos)
    for i, victim in enumerate(VICTIMS):
        event = _make_phishing_event(victim, ts_offset_secs=i * 30)  # 30s separados
        await publish_raw_event(redis_url, event)
        await asyncio.sleep(0.1)

    # Esperar incidente
    incident = await wait_for_incident(
        mongo_url=mongo_url,
        db_name=MONGO_DB,
        filter_query={
            "$or": [
                {"titulo": {"$regex": "phishing",  "$options": "i"}},
                {"titulo": {"$regex": "campaña",   "$options": "i"}},
                {"titulo": {"$regex": "multiple",  "$options": "i"}},
                {"titulo": {"$regex": "coordin",   "$options": "i"}},
            ]
        },
        timeout_secs=120
    )

    assert incident is not None, (
        f"El correlator NO detectó phishing coordinado al dominio {PHISHING_DOMAIN}. "
        "Verificar reglas de correlación multi-víctima."
    )

    # Verificar que el incidente referencia al menos 3 eventos (uno por víctima)
    eventos_ids = incident.get("eventos_ids", [])
    assert len(eventos_ids) >= 3, (
        f"El incidente de phishing debe referenciar >= 3 eventos. "
        f"Solo tiene: {len(eventos_ids)}"
    )

    # Verificar que NO se generaron 3 incidentes separados (sino 1 agrupado)
    total = await count_incidents(
        mongo_url=mongo_url,
        db_name=MONGO_DB,
        filter_query={
            "$or": [
                {"titulo": {"$regex": "phishing", "$options": "i"}},
                {"titulo": {"$regex": "campaña",  "$options": "i"}},
            ]
        }
    )

    assert total == 1, (
        f"El correlator creó {total} incidentes separados en lugar de 1 agrupado. "
        "Revisar lógica de deduplicación de campaña."
    )

    # Verificar severidad
    assert incident.get("severidad") in ("alta", "critica", "media"), (
        f"Severidad inesperada: {incident.get('severidad')}"
    )


@pytest.mark.timeout(90)
async def test_phishing_dominio_unico_no_es_campana(full_stack, clean_state):
    """
    1 solo usuario consulta un dominio sospechoso → puede ser incidente individual,
    pero NO debe clasificarse como campaña multi-víctima (no crea confusión en el SOC).
    """
    redis_url = full_stack["redis_url"]
    mongo_url = full_stack["mongo_url"]

    # Solo 1 víctima
    event = _make_phishing_event(VICTIMS[0])
    event["externo"]["valor"] = "sospechoso-una-sola-victima.xyz"
    await publish_raw_event(redis_url, event)

    await asyncio.sleep(60)

    # Verificar que no se generó incidente de CAMPAÑA (puede haber uno individual)
    count = await count_incidents(
        mongo_url=mongo_url,
        db_name=MONGO_DB,
        filter_query={
            "$or": [
                {"titulo": {"$regex": "campaña",   "$options": "i"}},
                {"titulo": {"$regex": "multiple",  "$options": "i"}},
                {"titulo": {"$regex": "coordin",   "$options": "i"}},
            ]
        }
    )

    assert count == 0, (
        f"Falso positivo: 1 victima generó un incidente de 'campaña coordinada' ({count}). "
        "Revisar umbral mínimo de víctimas en el correlator."
    )
