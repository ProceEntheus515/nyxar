"""Tests motor auto_response con Mongo en memoria."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from auto_response.approval import ApprovalManager
from auto_response.audit import AuditLogger
from auto_response.engine import ResponseEngine
from auto_response.models import AccionPropuesta, ResponsePlan


def _critico_incident_lateral():
    return {
        "id": "inc-ar-1",
        "severidad": "CRÍTICA",
        "host_afectado": "192.168.88.10",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "patron": "movimiento lateral sospechoso",
        "descripcion": "",
        "mitre_technique": "T1210",
        "evento_original_id": "e1",
        "detalles": {},
        "estado": "abierto",
    }


def _critico_incident_simple():
    return {
        "id": "inc-ar-2",
        "severidad": "CRITICA",
        "host_afectado": "192.168.1.5",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "patron": "alerta",
        "descripcion": "sin expansion",
        "mitre_technique": "T1001",
        "evento_original_id": "e2",
        "detalles": {},
        "estado": "abierto",
    }


@pytest.mark.v2
@pytest.mark.asyncio
async def test_propuesta_creada(monkeypatch, mongo_client_mock, mem_db):
    monkeypatch.setenv("AUTO_RESPONSE_CRITICO", "false")
    redis = MagicMock()
    redis.try_acquire_rate_slot = AsyncMock(return_value=True)
    redis.publish_alert = AsyncMock()
    redis.client = True
    eng = ResponseEngine(mongo=mongo_client_mock, redis_bus=redis)
    await eng._ensure_indexes()
    pid = await eng.propose_actions(_critico_incident_simple(), force_auto_approve=False)
    assert pid
    doc = await mem_db.response_proposals.find_one({"id": pid})
    assert doc and doc.get("estado") == "pendiente_aprobacion"
    assert any(x.get("tipo") == "propuesta" for x in mem_db.audit_log.rows)


@pytest.mark.v2
@pytest.mark.asyncio
async def test_auto_approve_disabled(monkeypatch, mongo_client_mock, mem_db):
    monkeypatch.setenv("AUTO_RESPONSE_CRITICO", "false")
    redis = MagicMock()
    redis.try_acquire_rate_slot = AsyncMock(return_value=True)
    redis.publish_alert = AsyncMock()
    redis.client = True
    eng = ResponseEngine(mongo=mongo_client_mock, redis_bus=redis)
    await eng._ensure_indexes()
    pid = await eng.propose_actions(_critico_incident_lateral(), force_auto_approve=False)
    doc = await mem_db.response_proposals.find_one({"id": pid})
    assert doc["estado"] == "pendiente_aprobacion"


@pytest.mark.v2
@pytest.mark.asyncio
async def test_auto_approve_enabled(monkeypatch, mongo_client_mock, mem_db):
    monkeypatch.setenv("AUTO_RESPONSE_CRITICO", "true")
    redis = MagicMock()
    redis.try_acquire_rate_slot = AsyncMock(return_value=True)
    redis.publish_alert = AsyncMock()
    redis.client = True
    eng = ResponseEngine(mongo=mongo_client_mock, redis_bus=redis)
    await eng._ensure_indexes()
    monkeypatch.setattr(eng, "execute_approved", AsyncMock(return_value={"exito": True}))
    pid = await eng.propose_actions(_critico_incident_lateral(), force_auto_approve=None)
    doc = await mem_db.response_proposals.find_one({"id": pid})
    assert doc["estado"] == "aprobado"
    eng.execute_approved.assert_awaited()


@pytest.mark.v2
@pytest.mark.asyncio
async def test_approve_ejecuta(monkeypatch, mongo_client_mock, mem_db):
    monkeypatch.setenv("AUTO_RESPONSE_CRITICO", "false")
    redis = MagicMock()
    redis.try_acquire_rate_slot = AsyncMock(return_value=True)
    redis.publish_alert = AsyncMock()
    redis.client = True
    eng = ResponseEngine(mongo=mongo_client_mock, redis_bus=redis)
    await eng._ensure_indexes()
    plan = ResponsePlan(
        incident_id="inc-exec",
        playbook_nombre="critical_notify",
        acciones=[
            AccionPropuesta(
                tipo="notify_only",
                objetivo="inc-exec",
                descripcion="n",
                reversible=True,
                impacto="bajo",
                requiere_aprobacion=False,
            )
        ],
        justificacion="t",
        urgencia="proxima_hora",
    )
    pid = "prop-exec-1"
    await mem_db.incidents.insert_one({"id": "inc-exec", "estado": "abierto", "severidad": "ALTA"})
    await mem_db.response_proposals.insert_one(
        {
            "id": pid,
            "incident_id": "inc-exec",
            "estado": "pendiente_aprobacion",
            "plan": plan.model_dump(mode="json"),
            "resultados": [],
            "creado_at": datetime.now(timezone.utc).isoformat(),
            "aprobado_at": None,
            "aprobado_by": None,
            "ejecutado_at": None,
        }
    )
    am = ApprovalManager(mongo_client_mock, redis, eng._audit)
    assert await am.approve(pid, "tester", "") is True
    res = await eng.execute_approved(pid)
    assert res.get("exito") is True
    assert len(mem_db.auto_response_audit.rows) >= 1


@pytest.mark.v2
@pytest.mark.asyncio
async def test_reject_no_ejecuta(monkeypatch, mongo_client_mock, mem_db):
    plan = ResponsePlan(
        incident_id="inc-rej",
        playbook_nombre="x",
        acciones=[
            AccionPropuesta(
                tipo="notify_only",
                objetivo="inc-rej",
                descripcion="n",
                reversible=True,
                impacto="bajo",
                requiere_aprobacion=False,
            )
        ],
        justificacion="t",
        urgencia="proxima_hora",
    )
    pid = "prop-rej"
    await mem_db.response_proposals.insert_one(
        {
            "id": pid,
            "incident_id": "inc-rej",
            "estado": "pendiente_aprobacion",
            "plan": plan.model_dump(mode="json"),
            "resultados": [],
            "creado_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    am = ApprovalManager(mongo_client_mock, None, AuditLogger(mongo_client_mock))
    assert await am.reject(pid, "u", "no") is True
    doc = await mem_db.response_proposals.find_one({"id": pid})
    assert doc["estado"] == "rechazado"
    eng = ResponseEngine(mongo=mongo_client_mock, redis_bus=MagicMock())
    res = await eng.execute_approved(pid)
    assert res.get("exito") is False


@pytest.mark.v2
@pytest.mark.asyncio
async def test_proposal_expira(monkeypatch, mongo_client_mock, mem_db):
    monkeypatch.setenv("APPROVAL_TIMEOUT", "1")
    old = (datetime.now(timezone.utc) - timedelta(hours=3)).isoformat()
    await mem_db.response_proposals.insert_one(
        {
            "id": "prop-exp",
            "incident_id": "inc-e",
            "estado": "pendiente_aprobacion",
            "plan": {"playbook_nombre": "p", "incident_id": "inc-e", "acciones": [], "justificacion": "", "urgencia": "proxima_hora"},
            "creado_at": old,
        }
    )
    am = ApprovalManager(mongo_client_mock, None, AuditLogger(mongo_client_mock))
    n = await am.auto_expire()
    assert n >= 1
    doc = await mem_db.response_proposals.find_one({"id": "prop-exp"})
    assert doc["estado"] == "expirado"
