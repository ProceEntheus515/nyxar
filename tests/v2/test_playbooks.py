"""
Tests V2: playbooks SOAR (cuarentena, bloqueo IP, AD) con HTTP y AD mockeados.
Se valida que execute_approved deja rastro en audit_log y auto_response_audit.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from auto_response.audit import AuditLogger
from auto_response.engine import ResponseEngine
from auto_response.models import AccionPropuesta, ResponsePlan


def _httpx_client_cm(post_resp: httpx.Response | None = None, delete_resp: httpx.Response | None = None):
    post_resp = post_resp or httpx.Response(200, json={"id": "rule-1"}, request=httpx.Request("POST", "http://fw/x"))
    delete_resp = delete_resp or httpx.Response(204, request=httpx.Request("DELETE", "http://fw/x"))

    inner = MagicMock()
    inner.post = AsyncMock(return_value=post_resp)
    inner.delete = AsyncMock(return_value=delete_resp)

    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=inner)
    cm.__aexit__ = AsyncMock(return_value=False)
    return cm, inner


async def _seed_proposal(mem_db, *, accion_tipo: str, objetivo: str, incident_id: str = "inc-pb-1") -> str:
    plan = ResponsePlan(
        incident_id=incident_id,
        playbook_nombre="TestPB",
        acciones=[
            AccionPropuesta(
                tipo=accion_tipo,  # type: ignore[arg-type]
                objetivo=objetivo,
                descripcion="test",
                reversible=True,
                impacto="bajo",
                requiere_aprobacion=False,
            )
        ],
        justificacion="test",
    )
    pid = "proposal-pb-test"
    await mem_db.incidents.insert_one(
        {
            "id": incident_id,
            "severidad": "ALTA",
            "estado": "abierto",
            "timestamp": "2025-01-01T00:00:00+00:00",
        }
    )
    await mem_db.response_proposals.insert_one(
        {
            "id": pid,
            "incident_id": incident_id,
            "estado": "aprobado",
            "plan": plan.model_dump(mode="json"),
            "resultados": [],
            "creado_at": "2025-01-01T00:00:00+00:00",
            "aprobado_at": "2025-01-01T00:00:01+00:00",
            "aprobado_by": "pytest",
            "ejecutado_at": None,
        }
    )
    return pid


@pytest.mark.v2
async def test_quarantine_ip_interna(mongo_client_mock, redis_bus_fake, monkeypatch):
    monkeypatch.setenv("FIREWALL_API_URL", "http://firewall.test")
    monkeypatch.delenv("SWITCH_API_URL", raising=False)
    cm, _inner = _httpx_client_cm()
    pid = await _seed_proposal(mongo_client_mock.db, accion_tipo="quarantine", objetivo="192.168.50.10")
    eng = ResponseEngine(mongo_client_mock, redis_bus_fake)
    with patch("auto_response.playbooks.quarantine.httpx.AsyncClient", return_value=cm):
        with patch("asyncio.sleep", new_callable=AsyncMock):
            out = await eng.execute_approved(pid)
    assert out.get("exito") is True
    st = await mongo_client_mock.db.playbook_quarantine_state.find_one({"ip": "192.168.50.10"})
    assert st and st.get("activo") is True
    assert mongo_client_mock.db.audit_log.rows
    assert mongo_client_mock.db.auto_response_audit.rows


@pytest.mark.v2
async def test_quarantine_ip_externa_falla(mongo_client_mock, redis_bus_fake, monkeypatch):
    monkeypatch.setenv("FIREWALL_API_URL", "http://firewall.test")
    pid = await _seed_proposal(mongo_client_mock.db, accion_tipo="quarantine", objetivo="8.8.8.8")
    eng = ResponseEngine(mongo_client_mock, redis_bus_fake)
    with patch("asyncio.sleep", new_callable=AsyncMock):
        out = await eng.execute_approved(pid)
    assert out.get("exito") is True
    res = (out.get("resultados") or [])[0]
    assert res.get("exito") is False
    assert mongo_client_mock.db.audit_log.rows
    assert mongo_client_mock.db.auto_response_audit.rows


@pytest.mark.v2
async def test_block_ip_externa(mongo_client_mock, redis_bus_fake, monkeypatch):
    monkeypatch.setenv("FIREWALL_API_URL", "http://firewall.test")
    cm, _ = _httpx_client_cm(
        post_resp=httpx.Response(201, json={"id": "ext-9"}, request=httpx.Request("POST", "http://fw/x"))
    )
    # 203.0.113.0/24 es "documentation" pero ipaddress la trata como is_private=True;
    # usar IP publica real para el playbook de bloqueo externo.
    ext_ip = "1.1.1.1"
    pid = await _seed_proposal(mongo_client_mock.db, accion_tipo="block_ip", objetivo=ext_ip)
    eng = ResponseEngine(mongo_client_mock, redis_bus_fake)
    with patch("auto_response.playbooks.block_ip.httpx.AsyncClient", return_value=cm):
        with patch("asyncio.sleep", new_callable=AsyncMock):
            out = await eng.execute_approved(pid)
    assert out.get("exito") is True
    assert (out.get("resultados") or [{}])[0].get("exito") is True
    doc = await mongo_client_mock.db.playbook_block_ip_state.find_one({"ip": ext_ip})
    assert doc and doc.get("activo") is True
    assert mongo_client_mock.db.audit_log.rows


@pytest.mark.v2
async def test_block_ip_interna_rechazada(mongo_client_mock, redis_bus_fake, monkeypatch):
    monkeypatch.setenv("FIREWALL_API_URL", "http://firewall.test")
    pid = await _seed_proposal(mongo_client_mock.db, accion_tipo="block_ip", objetivo="10.0.0.5")
    eng = ResponseEngine(mongo_client_mock, redis_bus_fake)
    with patch("asyncio.sleep", new_callable=AsyncMock):
        out = await eng.execute_approved(pid)
    res = (out.get("resultados") or [])[0]
    assert res.get("exito") is False
    assert mongo_client_mock.db.audit_log.rows


@pytest.mark.v2
async def test_disable_user_ad_write_disabled(mongo_client_mock, redis_bus_fake, monkeypatch):
    monkeypatch.setenv("AD_WRITE_ENABLED", "false")
    pid = await _seed_proposal(
        mongo_client_mock.db,
        accion_tipo="disable_user",
        objetivo="usuario.test",
        incident_id="inc-ad-1",
    )
    eng = ResponseEngine(mongo_client_mock, redis_bus_fake)
    with patch("asyncio.sleep", new_callable=AsyncMock):
        out = await eng.execute_approved(pid)
    res = (out.get("resultados") or [])[0]
    assert res.get("exito") is False
    assert "AD_WRITE_ENABLED" in (res.get("detalle") or "")
    assert mongo_client_mock.db.audit_log.rows


@pytest.mark.v2
async def test_disable_user_admin_rechazado(mongo_client_mock, redis_bus_fake, monkeypatch):
    monkeypatch.setenv("AD_WRITE_ENABLED", "true")
    monkeypatch.setenv("AD_SERVER", "ldap.test")
    monkeypatch.setenv("AD_BASE_DN", "DC=test,DC=local")
    monkeypatch.setenv("AD_USER", "CN=svc,DC=test,DC=local")
    monkeypatch.setenv("AD_PASSWORD", "x")
    pid = await _seed_proposal(
        mongo_client_mock.db,
        accion_tipo="disable_user",
        objetivo="badadmin",
        incident_id="inc-ad-2",
    )

    async def fake_get_user(_sam: str):
        return {
            "distinguishedName": "CN=badadmin,DC=test,DC=local",
            "memberOf": ["CN=Domain Admins,CN=Users,DC=test,DC=local"],
            "userAccountControl": 512,
        }

    eng = ResponseEngine(mongo_client_mock, redis_bus_fake)
    with patch("auto_response.playbooks.disable_user.ADClient") as m_ad:
        inst = m_ad.return_value
        inst.is_configured = MagicMock(return_value=True)
        inst.get_user_by_sam = AsyncMock(side_effect=fake_get_user)
        inst.close = MagicMock()
        with patch("asyncio.sleep", new_callable=AsyncMock):
            out = await eng.execute_approved(pid)
    res = (out.get("resultados") or [])[0]
    assert res.get("exito") is False
    det = (res.get("detalle") or "").lower()
    assert "domain admin" in det or "miembro" in det
    assert mongo_client_mock.db.audit_log.rows


@pytest.mark.v2
async def test_quarantine_idempotente(mongo_client_mock, redis_bus_fake, monkeypatch):
    monkeypatch.setenv("FIREWALL_API_URL", "http://firewall.test")
    cm, inner = _httpx_client_cm()
    pid = await _seed_proposal(mongo_client_mock.db, accion_tipo="quarantine", objetivo="192.168.60.2")
    eng = ResponseEngine(mongo_client_mock, redis_bus_fake)
    with patch("auto_response.playbooks.quarantine.httpx.AsyncClient", return_value=cm):
        with patch("asyncio.sleep", new_callable=AsyncMock):
            await eng.execute_approved(pid)
            await eng.execute_approved(pid)
    assert inner.post.await_count == 1


@pytest.mark.v2
async def test_undo_quarantine(mongo_client_mock, redis_bus_fake, monkeypatch):
    monkeypatch.setenv("FIREWALL_API_URL", "http://firewall.test")
    cm_post, inner = _httpx_client_cm()
    cm_del = MagicMock()
    cm_del.__aenter__ = AsyncMock(return_value=inner)
    cm_del.__aexit__ = AsyncMock(return_value=False)

    from auto_response.playbooks.quarantine import QuarantinePlaybook

    pb = QuarantinePlaybook(mongo_client_mock, redis_bus_fake)
    accion = AccionPropuesta(
        tipo="quarantine",
        objetivo="192.168.70.3",
        descripcion="x",
        reversible=True,
        impacto="x",
        requiere_aprobacion=False,
    )
    ctx = {"incident_id": "inc-undo", "ejecutado_by": "t"}
    with patch("auto_response.playbooks.quarantine.httpx.AsyncClient", return_value=cm_post):
        out = await pb.execute(accion, ctx)
    assert out.get("exito") is True
    eid = out.get("execution_id")
    assert eid
    with patch("auto_response.playbooks.quarantine.httpx.AsyncClient", return_value=cm_del):
        undo = await pb.undo(eid)
    assert undo.exitoso is True
    assert inner.delete.await_count >= 1

    await AuditLogger(mongo_client_mock).log_action(
        tipo="resultado",
        proposal_id="undo-test",
        actor="pytest",
        incident_id="inc-undo",
        playbook="quarantine",
        objetivo="192.168.70.3",
        detalle={"undo": True},
        exitoso=True,
    )
    assert mongo_client_mock.db.audit_log.rows
