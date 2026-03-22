"""Tests del motor auto_response (sin Mongo real)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from auto_response.engine import ResponseEngine
from auto_response.models import AccionPropuesta, ResponsePlan
from auto_response.playbook_select import classify_patron_keys, normalize_severidad


def test_normalize_severidad_critica_tilde():
    assert normalize_severidad({"severidad": "CRÍTICA"}) == "CRITICA"


def test_classify_patron_beaconing():
    keys = classify_patron_keys(
        {"patron": "Beaconing (C2 Communication)", "descripcion": ""}
    )
    assert "beaconing" in keys


def test_evaluate_incident_alta_beaconing():
    inc = {
        "id": "INC-1",
        "patron": "Beaconing (C2 Communication)",
        "descripcion": "",
        "severidad": "ALTA",
        "host_afectado": "10.0.0.5",
        "detalles": {},
    }
    plan = ResponseEngine.evaluate_incident(inc)
    assert plan is not None
    tipos = [a.tipo for a in plan.acciones]
    assert "block_ip" in tipos
    assert "notify_only" in tipos


def test_evaluate_incident_critica_lateral():
    inc = {
        "id": "INC-2",
        "patron": "Movimiento Lateral (Escaneo Horizontal o DC Access)",
        "descripcion": "",
        "severidad": "CRITICA",
        "host_afectado": "10.0.0.9",
        "detalles": {},
    }
    plan = ResponseEngine.evaluate_incident(inc)
    assert plan is not None
    tipos = [a.tipo for a in plan.acciones]
    assert "quarantine" in tipos
    assert "notify_only" in tipos


def test_evaluate_incident_honeypot_with_user():
    inc = {
        "id": "INC-3",
        "patron": "TRAMPILLA_HONEYPOT",
        "descripcion": "Honeypot",
        "severidad": "CRITICA",
        "host_afectado": "203.0.113.50",
        "detalles": {"usuario": "dom\\svc_bad"},
    }
    plan = ResponseEngine.evaluate_incident(inc)
    assert plan is not None
    assert any(a.tipo == "disable_user" for a in plan.acciones)


def test_evaluate_incident_baja_returns_none():
    inc = {
        "id": "INC-4",
        "patron": "Beaconing (C2 Communication)",
        "severidad": "BAJA",
        "host_afectado": "10.0.0.1",
        "detalles": {},
    }
    assert ResponseEngine.evaluate_incident(inc) is None


@pytest.mark.asyncio
async def test_propose_skips_when_active_proposal_exists():
    engine = ResponseEngine()
    engine.has_active_proposal = AsyncMock(return_value=True)
    out = await engine.propose_actions({"id": "X", "severidad": "ALTA", "patron": "beaconing"})
    assert out is None


@pytest.mark.asyncio
async def test_execute_approved_rejects_pendiente():
    engine = ResponseEngine()
    proposals = MagicMock()
    proposals.find_one_and_update = AsyncMock(return_value=None)
    proposals.find_one = AsyncMock(
        return_value={"id": "p1", "estado": "pendiente_aprobacion"}
    )

    class DB:
        def __getitem__(self, name):
            if name == "response_proposals":
                return proposals
            return MagicMock()

    engine.mongo = MagicMock()
    engine.mongo.db = DB()

    r = await engine.execute_approved("p1")
    assert r.get("exito") is False
    assert r.get("code") == "INVALID_STATE"


@pytest.mark.asyncio
async def test_execute_approved_throttle_between_actions():
    plan = ResponsePlan(
        incident_id="INC-T",
        playbook_nombre="test",
        acciones=[
            AccionPropuesta(
                tipo="notify_only",
                objetivo="INC-T",
                descripcion="Primera notificacion de prueba",
                reversible=True,
                impacto="Bajo",
                requiere_aprobacion=False,
            ),
            AccionPropuesta(
                tipo="notify_only",
                objetivo="INC-T",
                descripcion="Segunda notificacion de prueba",
                reversible=True,
                impacto="Bajo",
                requiere_aprobacion=False,
            ),
        ],
        justificacion="test",
        urgencia="proxima_hora",
    )

    proposals = MagicMock()
    proposals.find_one_and_update = AsyncMock(
        return_value={"plan": plan.model_dump(mode="json"), "estado": "aprobado"}
    )
    proposals.update_one = AsyncMock()

    audit = MagicMock()
    audit.insert_one = AsyncMock()

    incidents = MagicMock()
    incidents.update_one = AsyncMock()

    class DB:
        def __init__(self) -> None:
            self.incidents = incidents

        def __getitem__(self, name):
            if name == "response_proposals":
                return proposals
            if name == "auto_response_audit":
                return audit
            if name == "incidents":
                return incidents
            return MagicMock()

    engine = ResponseEngine()
    engine.mongo = MagicMock()
    engine.mongo.db = DB()

    with patch("auto_response.engine.asyncio.sleep", new_callable=AsyncMock) as sleep_mock:
        r = await engine.execute_approved("prop-1")

    assert r.get("exito") is True
    assert sleep_mock.await_count == 1
