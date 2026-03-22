"""
E2E: Tests de Falsos Positivos — CRÍTICOS para la confianza del SOC

Los falsos positivos desgastan al equipo de seguridad. Estos tests verifican
que el sistema NO alerta sobre comportamientos normales esperados del baseline.

Filosofía: Un sistema que alerta sobre todo, no alerta sobre nada.
"""

import pytest
import asyncio
from datetime import datetime, timezone, timedelta

from tests.e2e.conftest_e2e import (
    publish_raw_event, count_incidents,
    get_identity_risk_score, MONGO_DB
)

pytestmark = [pytest.mark.e2e, pytest.mark.asyncio]


def _make_event(source: str, tipo: str, ip: str, hostname: str,
                usuario: str, area: str, externo_valor: str, externo_tipo: str,
                ts_offset_secs: int = 0, detalles: dict = None) -> dict:
    """Factory genérica para eventos raw."""
    ts = (datetime.now(timezone.utc) + timedelta(seconds=ts_offset_secs)).isoformat()
    return {
        "source": source,
        "tipo": tipo,
        "timestamp": ts,
        "interno": {
            "ip": ip,
            "hostname": hostname,
            "usuario": usuario,
            "area": area
        },
        "externo": {
            "valor": externo_valor,
            "tipo": externo_tipo
        },
        "detalles": detalles or {}
    }


# ---------------------------------------------------------------------------
# FP-01: Reunión de equipo viendo YouTube NO es phishing
# ---------------------------------------------------------------------------

@pytest.mark.timeout(90)
async def test_reunion_equipo_no_es_phishing(full_stack, clean_state):
    """
    3 usuarios del mismo área consultan youtube.com en 30 minutos.
    (Están viendo un video juntos en sala de reuniones).
    youtube.com está en lista de dominios conocidos/permitidos.
    Verificar que NO se genera incidente de phishing coordinado.
    """
    redis_url = full_stack["redis_url"]
    mongo_url = full_stack["mongo_url"]

    team_members = [
        {"ip": "192.168.50.11", "user": "marketing.lopez",   "host": "mkt-lopez-pc"},
        {"ip": "192.168.50.12", "user": "marketing.vargas",  "host": "mkt-vargas-pc"},
        {"ip": "192.168.50.13", "user": "marketing.castro",  "host": "mkt-castro-pc"},
    ]

    for i, member in enumerate(team_members):
        event = _make_event(
            source="dns", tipo="query",
            ip=member["ip"], hostname=member["host"],
            usuario=member["user"], area="Marketing",
            externo_valor="youtube.com", externo_tipo="dominio",
            ts_offset_secs=i * 300,  # 5 min entre cada uno
            detalles={"query_type": "A", "status": "NOERROR"}
        )
        await publish_raw_event(redis_url, event)

    await asyncio.sleep(60)

    # NO debe haber incidente de phishing ni campaña
    count = await count_incidents(
        mongo_url=mongo_url,
        db_name=MONGO_DB,
        filter_query={
            "$or": [
                {"titulo": {"$regex": "phishing",  "$options": "i"}},
                {"titulo": {"$regex": "campaña",   "$options": "i"}},
                {"titulo": {"$regex": "coordin",   "$options": "i"}},
            ]
        }
    )

    assert count == 0, (
        f"FALSO POSITIVO CRÍTICO: La reunión de equipo viendo youtube.com "
        f"generó {count} incidente(s) de phishing. "
        "Agregar youtube.com a lista de dominios permitidos del correlator."
    )


# ---------------------------------------------------------------------------
# FP-02: Backup nocturno NO es exfiltración de datos
# ---------------------------------------------------------------------------

@pytest.mark.timeout(90)
async def test_backup_nocturno_no_es_exfiltracion(full_stack, clean_state):
    """
    El servidor de backup genera tráfico masivo a las 2am (backup programado).
    La identidad del servidor tiene este patrón registrado en su baseline.
    Verificar que el sistema NO lo detecta como exfiltración.
    """
    redis_url = full_stack["redis_url"]
    mongo_url = full_stack["mongo_url"]

    # Primero: registrar baseline del servidor de backup en MongoDB
    import motor.motor_asyncio
    mongo = motor.motor_asyncio.AsyncIOMotorClient(mongo_url)
    db = mongo[MONGO_DB]
    await db.identities.insert_one({
        "id": "sistema.backup",
        "usuario": "sistema.backup",
        "area": "IT",
        "dispositivo": "backup-server-01",
        "hostname": "backup-server-01",
        "risk_score_actual": 0,
        "baseline": {
            "horario_inicio": "01:00",
            "horario_fin": "05:00",
            "dias_laborales": ["lunes", "martes", "miercoles", "jueves", "viernes"],
            "dominios_habituales": ["backup.empresa.local", "nas01.empresa.local"],
            "volumen_mb_dia_media": 2048.0,
            "volumen_mb_dia_std": 512.0,
            "servidores_internos": ["nas01", "nas02", "dc01"],
            "muestras_recolectadas": 90,
            "baseline_valido": True
        }
    })
    mongo.close()

    # Inyectar eventos de backup masivo dentro de la ventana horaria esperada
    for i in range(15):  # 15 eventos de transferencia
        event = _make_event(
            source="firewall", tipo="request",
            ip="192.168.100.5", hostname="backup-server-01",
            usuario="sistema.backup", area="IT",
            externo_valor="nas01.empresa.local", externo_tipo="ip",
            ts_offset_secs=i * 60,  # 1 evento por minuto
            detalles={"bytes_transferidos": 150000000, "puerto_dst": 445}
        )
        await publish_raw_event(redis_url, event)

    await asyncio.sleep(60)

    # NO debe generar incidente de exfiltración
    count = await count_incidents(
        mongo_url=mongo_url,
        db_name=MONGO_DB,
        filter_query={
            "$or": [
                {"titulo": {"$regex": "exfiltr",       "$options": "i"}},
                {"titulo": {"$regex": "data.loss",     "$options": "i"}},
                {"titulo": {"$regex": "volumen.inusual","$options": "i"}},
            ],
            "host_afectado": {"$regex": "backup", "$options": "i"}
        }
    )

    assert count == 0, (
        f"FALSO POSITIVO: El backup nocturno del servidor generó {count} "
        "incidente(s) de exfiltración. El correlator debe verificar contra el baseline."
    )


# ---------------------------------------------------------------------------
# FP-03: Admin de IT accediendo servidores NO es movimiento lateral
# ---------------------------------------------------------------------------

@pytest.mark.timeout(90)
async def test_desarrollador_it_accediendo_servidores(full_stack, clean_state):
    """
    Usuario de IT accede a dc01.local, fileserver01, y backup01 en 10 minutos.
    Su baseline incluye esos servidores como acceso rutinario.
    Verificar que NO se genera alerta de movimiento lateral.
    """
    redis_url = full_stack["redis_url"]
    mongo_url = full_stack["mongo_url"]

    # Registrar baseline del admin IT
    import motor.motor_asyncio
    mongo = motor.motor_asyncio.AsyncIOMotorClient(mongo_url)
    db = mongo[MONGO_DB]
    await db.identities.insert_one({
        "id": "it.ramirez",
        "usuario": "it.ramirez",
        "area": "IT",
        "dispositivo": "it-ramirez-pc",
        "hostname": "it-ramirez-pc",
        "risk_score_actual": 5,
        "baseline": {
            "horario_inicio": "08:00",
            "horario_fin": "18:00",
            "dias_laborales": ["lunes", "martes", "miercoles", "jueves", "viernes"],
            "dominios_habituales": [],
            "volumen_mb_dia_media": 500.0,
            "volumen_mb_dia_std": 200.0,
            "servidores_internos": [
                "dc01.empresa.local", "fileserver01.empresa.local",
                "backup01.empresa.local", "siem.empresa.local"
            ],
            "muestras_recolectadas": 120,
            "baseline_valido": True
        }
    })
    mongo.close()

    # Accesos rutinarios del admin dentro de su baseline
    servers = [
        "dc01.empresa.local",
        "fileserver01.empresa.local",
        "backup01.empresa.local"
    ]

    for i, server in enumerate(servers):
        event = _make_event(
            source="firewall", tipo="request",
            ip="192.168.1.200", hostname="it-ramirez-pc",
            usuario="it.ramirez", area="IT",
            externo_valor=server, externo_tipo="dominio",
            ts_offset_secs=i * 120,  # Cada 2 minutos
            detalles={"puerto_dst": 22, "protocolo": "SSH"}
        )
        await publish_raw_event(redis_url, event)

    await asyncio.sleep(60)

    # NO debe generar movimiento lateral
    count = await count_incidents(
        mongo_url=mongo_url,
        db_name=MONGO_DB,
        filter_query={
            "$or": [
                {"titulo": {"$regex": "lateral",    "$options": "i"}},
                {"titulo": {"$regex": "movimiento", "$options": "i"}},
                {"titulo": {"$regex": "pivoting",   "$options": "i"}},
            ],
            "host_afectado": {"$regex": "it.ramirez", "$options": "i"}
        }
    )

    assert count == 0, (
        f"FALSO POSITIVO: El admin de IT accediendo a {len(servers)} servidores "
        f"de su baseline generó {count} incidente(s) de movimiento lateral. "
        "El correlator debe cruzar los accesos contra la lista de servidores del baseline."
    )

    # El risk_score post-acceso rutinario debe mantenerse bajo
    score = await get_identity_risk_score(mongo_url, MONGO_DB, "it.ramirez")
    assert score < 40, (
        f"Risk score del admin IT tras accesos de baseline escaló a {score}. "
        "Debería permanecer bajo (<40) para actividad rutinaria."
    )


# ---------------------------------------------------------------------------
# FP-04: Alto volumen de DNS queries de servidor de monitoreo
# ---------------------------------------------------------------------------

@pytest.mark.timeout(90)
async def test_servidor_monitoreo_no_es_tunneling(full_stack, clean_state):
    """
    Un servidor de monitoreo (Nagios/Zabbix) hace cientos de DNS lookups
    para verificar disponibilidad de servicios externos.
    Verificar que NO se detecta como DNS tunneling o beaconing.
    """
    redis_url = full_stack["redis_url"]
    mongo_url = full_stack["mongo_url"]

    # Monitoreo: 50 queries a dominios DISTINTOS (no mismo dominio repetido)
    monitored_services = [
        f"service-{i:03d}.empresa-cliente-{(i % 5) + 1}.com"
        for i in range(50)
    ]

    for i, domain in enumerate(monitored_services):
        event = _make_event(
            source="dns", tipo="query",
            ip="192.168.100.10", hostname="monitoring-server",
            usuario="sistema.monitoreo", area="IT",
            externo_valor=domain, externo_tipo="dominio",
            ts_offset_secs=i * 30,
            detalles={"query_type": "A", "status": "NOERROR"}
        )
        await publish_raw_event(redis_url, event)

    await asyncio.sleep(60)

    # NO debe detectar tunneling (los subdominios son cortos y normales)
    count = await count_incidents(
        mongo_url=mongo_url,
        db_name=MONGO_DB,
        filter_query={
            "$or": [
                {"titulo": {"$regex": "tunnel",    "$options": "i"}},
                {"titulo": {"$regex": "beaconing", "$options": "i"}},
            ],
            "host_afectado": {"$regex": "monitoreo", "$options": "i"}
        }
    )

    assert count == 0, (
        f"FALSO POSITIVO: El servidor de monitoreo generó {count} incidente(s) "
        "de tunneling/beaconing. Agregar identidad del servidor a whitelist de monitoreo."
    )
