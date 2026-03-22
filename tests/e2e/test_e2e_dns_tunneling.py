"""
E2E: Detección de DNS Tunneling (Exfiltración de datos via DNS)

Escenario: Un host envía consultas DNS con subdominios extremadamente largos
y codificados en base64 hacia un dominio controlado por el atacante.
Este patrón es característico de herramientas como dnscat2 o iodine.
"""

import pytest
import asyncio
import base64
from datetime import datetime, timezone, timedelta

from tests.e2e.conftest_e2e import (
    publish_raw_event, wait_for_incident,
    get_identity_risk_score, MONGO_DB
)

pytestmark = [pytest.mark.e2e, pytest.mark.asyncio]

TUNNEL_TARGET_ID  = "it.hernandez"
TUNNEL_TARGET_IP  = "192.168.40.77"
TUNNEL_BASE_DOMAIN = "exfil-channel-c2.xyz"


def _encode_chunk(data: str) -> str:
    """Simula payload codificado en base64 como subdominio DNS."""
    return base64.b32encode(data.encode()).decode().replace("=", "").lower()


def _make_tunnel_dns_event(subdomain: str, ts_offset_secs: int = 0) -> dict:
    full_domain = f"{subdomain}.{TUNNEL_BASE_DOMAIN}"
    ts = (datetime.now(timezone.utc) + timedelta(seconds=ts_offset_secs)).isoformat()
    return {
        "source": "dns",
        "tipo": "query",
        "timestamp": ts,
        "interno": {
            "ip": TUNNEL_TARGET_IP,
            "hostname": "it-hernandez-pc",
            "usuario": TUNNEL_TARGET_ID,
            "area": "IT"
        },
        "externo": {
            "valor": full_domain,
            "tipo": "dominio"
        },
        "detalles": {
            "query_type": "TXT",
            "subdomain_length": len(subdomain),
            "full_domain": full_domain
        }
    }


@pytest.mark.timeout(180)
async def test_dns_tunneling_detectado(full_stack, clean_state):
    """
    1. Inyectar 20+ consultas DNS con subdominios largos codificados (>50 chars).
    2. Hacia el mismo dominio base (C2).
    3. Verificar incidente de DNS tunneling o exfiltración DNS generado.
    4. Risk score del host > 70.
    """
    redis_url = full_stack["redis_url"]
    mongo_url = full_stack["mongo_url"]

    # Simular chunks de datos exfiltrados como subdominios
    fake_payloads = [
        "user_credentials_dump_chunk_001_of_020",
        "user_credentials_dump_chunk_002_of_020",
        "database_export_row_batch_003_of_020",
        "database_export_row_batch_004_of_020",
        "private_key_pem_b64_chunk_005_of_020",
        "ssh_config_backup_chunk_006_of_020",
        "shadow_file_dump_chunk_007_of_020",
        "network_map_export_chunk_008_of_020",
        "ad_users_list_dump_chunk_009_of_020",
        "browser_passwords_chunk_010_of_020",
        "database_export_row_batch_011_of_020",
        "database_export_row_batch_012_of_020",
        "user_credentials_dump_chunk_013_of_020",
        "private_key_pem_b64_chunk_014_of_020",
        "ssh_config_backup_chunk_015_of_020",
        "shadow_file_dump_chunk_016_of_020",
        "network_map_export_chunk_017_of_020",
        "ad_users_list_dump_chunk_018_of_020",
        "browser_passwords_chunk_019_of_020",
        "final_transfer_end_marker_020_of_020",
    ]

    for i, payload in enumerate(fake_payloads):
        subdomain = _encode_chunk(payload)           # Subdominio largo codificado
        event = _make_tunnel_dns_event(subdomain, ts_offset_secs=i * 3)
        await publish_raw_event(redis_url, event)
        await asyncio.sleep(0.05)

    # Esperar detección por el correlator
    incident = await wait_for_incident(
        mongo_url=mongo_url,
        db_name=MONGO_DB,
        filter_query={
            "$or": [
                {"titulo": {"$regex": "dns.tunnel",  "$options": "i"}},
                {"titulo": {"$regex": "tunneling",   "$options": "i"}},
                {"titulo": {"$regex": "exfiltr",     "$options": "i"}},
                {"titulo": {"$regex": "dns.exfil",   "$options": "i"}},
            ],
            "host_afectado": {"$regex": TUNNEL_TARGET_ID, "$options": "i"},
        },
        timeout_secs=120
    )

    assert incident is not None, (
        "El correlator NO detectó DNS Tunneling. "
        "Verificar heurística de longitud de subdominios y query rate en correlator."
    )
    assert incident.get("severidad") in ("alta", "critica"), (
        f"DNS Tunneling debe ser alta/critica. Obtenido: {incident.get('severidad')}"
    )

    score = await get_identity_risk_score(mongo_url, MONGO_DB, TUNNEL_TARGET_ID)
    assert score > 70, f"Risk score post-tunneling debe ser >70. Obtenido: {score}"


@pytest.mark.timeout(90)
async def test_consulta_txt_normal_no_es_tunneling(full_stack, clean_state):
    """
    Consultas TXT normales (SPF, DMARC records) no deben ser detectadas como tunneling.
    """
    from tests.e2e.conftest_e2e import count_incidents
    redis_url = full_stack["redis_url"]
    mongo_url = full_stack["mongo_url"]

    # Consultas TXT legítimas (SPF, DMARC)
    legitimate_txt_queries = [
        ("v=spf1", "google.com"),
        ("_dmarc",    "microsoft.com"),
        ("_domainkey", "gmail.com"),
    ]
    for subdomain, domain in legitimate_txt_queries:
        event = {
            "source": "dns",
            "tipo": "query",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "interno": {
                "ip": "192.168.1.5",
                "hostname": "mail-server",
                "usuario": "sistema.mail",
                "area": "IT"
            },
            "externo": {
                "valor": f"{subdomain}.{domain}",
                "tipo": "dominio"
            },
            "detalles": {"query_type": "TXT"}
        }
        await publish_raw_event(redis_url, event)

    await asyncio.sleep(60)

    count = await count_incidents(
        mongo_url=mongo_url,
        db_name=MONGO_DB,
        filter_query={
            "$or": [
                {"titulo": {"$regex": "tunneling", "$options": "i"}},
                {"titulo": {"$regex": "exfiltr",   "$options": "i"}},
            ]
        }
    )

    assert count == 0, (
        f"Falso positivo: consultas TXT legítimas (SPF/DMARC) "
        f"generaron {count} incidente(s) de DNS tunneling."
    )
