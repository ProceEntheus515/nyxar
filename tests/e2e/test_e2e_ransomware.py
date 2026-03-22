"""
E2E: Detección de Ransomware (Cifrado Masivo de Archivos)

Escenario: Un host interno genera una ráfaga de escrituras SMB masivas en 
un tiempo muy corto + consultas a dominios de pago (TOR, crypto), indicando
un proceso de cifrado activo.
"""

import pytest
import asyncio
from datetime import datetime, timezone, timedelta

from tests.e2e.conftest_e2e import (
    publish_raw_event, wait_for_incident,
    get_identity_risk_score, MONGO_DB
)

pytestmark = [pytest.mark.e2e, pytest.mark.asyncio]

RANSOM_TARGET_ID  = "finanzas.rodriguez"
RANSOM_TARGET_IP  = "192.168.30.55"
RANSOM_DOMAIN_TOR = "pay-now-files-decrypt.onion.to"
RANSOM_DOMAIN_BTC = "bitcoin-ransom-payment-3f9a.xyz"


def _make_wazuh_event(ts_offset_secs: int = 0, rule_level: int = 12,
                       desc: str = "Possible ransomware activity detected") -> dict:
    ts = (datetime.now(timezone.utc) + timedelta(seconds=ts_offset_secs)).isoformat()
    return {
        "source": "wazuh",
        "tipo": "alert",
        "timestamp": ts,
        "interno": {
            "ip": RANSOM_TARGET_IP,
            "hostname": "finanzas-rodriguez-pc",
            "usuario": RANSOM_TARGET_ID,
            "area": "Finanzas"
        },
        "externo": {
            "valor": desc,
            "tipo": "hash"
        },
        "detalles": {"rule_level": rule_level, "rule_desc": desc}
    }


def _make_dns_ransom_event(domain: str, ts_offset_secs: int = 0) -> dict:
    ts = (datetime.now(timezone.utc) + timedelta(seconds=ts_offset_secs)).isoformat()
    return {
        "source": "dns",
        "tipo": "query",
        "timestamp": ts,
        "interno": {
            "ip": RANSOM_TARGET_IP,
            "hostname": "finanzas-rodriguez-pc",
            "usuario": RANSOM_TARGET_ID,
            "area": "Finanzas"
        },
        "externo": {
            "valor": domain,
            "tipo": "dominio"
        },
        "detalles": {"query_type": "A"}
    }


@pytest.mark.timeout(180)
async def test_ransomware_detectado(full_stack, clean_state):
    """
    1. Inyectar múltiples alertas Wazuh de manipulación masiva de archivos.
    2. Inyectar consultas DNS a dominios de pago de rescate.
    3. Verificar que el correlator genera incidente de ransomware con severidad crítica.
    4. Verificar que el risk_score del host > 80.
    """
    redis_url = full_stack["redis_url"]
    mongo_url = full_stack["mongo_url"]

    # Rafaga de eventos Wazuh (múltiples archivos cifrados en segundos)
    ransom_descs = [
        "Mass file rename with encrypted extension (.locked)",
        "Mass file rename with encrypted extension (.locked)",
        "Shadow copy deletion detected (vssadmin)",
        "High volume file write operations in short time",
        "Suspicious process accessing many files simultaneously",
        "Mass file rename with encrypted extension (.locked)",
        "Backup deletion command detected",
    ]
    for i, desc in enumerate(ransom_descs):
        ev = _make_wazuh_event(ts_offset_secs=i * 10, rule_level=12, desc=desc)
        await publish_raw_event(redis_url, ev)
        await asyncio.sleep(0.05)

    # Consultas a dominios de pago de rescate
    for domain in [RANSOM_DOMAIN_TOR, RANSOM_DOMAIN_BTC]:
        ev = _make_dns_ransom_event(domain, ts_offset_secs=90)
        await publish_raw_event(redis_url, ev)

    # Esperar detección
    incident = await wait_for_incident(
        mongo_url=mongo_url,
        db_name=MONGO_DB,
        filter_query={
            "$or": [
                {"titulo": {"$regex": "ransomware", "$options": "i"}},
                {"titulo": {"$regex": "cifrado",    "$options": "i"}},
                {"titulo": {"$regex": "ransom",     "$options": "i"}},
                {"titulo": {"$regex": "encrypt",    "$options": "i"}},
            ],
            "host_afectado": {"$regex": RANSOM_TARGET_ID, "$options": "i"},
        },
        timeout_secs=120
    )

    assert incident is not None, (
        "El correlator NO detectó el ransomware activo. "
        "Revisar reglas para patrones de cifrado masivo + DNS de C2."
    )
    assert incident.get("severidad") == "critica", (
        f"Ransomware debe ser CRÍTICO. Obtenido: {incident.get('severidad')}"
    )

    # Risk score del host debe ser muy alto post-ransomware
    score = await get_identity_risk_score(mongo_url, MONGO_DB, RANSOM_TARGET_ID)
    assert score > 80, (
        f"Risk score post-ransomware debe ser >80. Obtenido: {score}"
    )
