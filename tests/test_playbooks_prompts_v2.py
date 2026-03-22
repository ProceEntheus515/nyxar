"""Cobertura ligera para playbooks alineados a PROMPTS_V2."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from auto_response.models import AccionPropuesta, PlaybookResult
from auto_response.playbooks.base import playbook_result_to_audit_dict
from auto_response.playbooks.block_ip import BlockIPPlaybook
from auto_response.playbooks.notify import CHANNEL_URGENT, NotifyOnlyPlaybook
from shared import ip_utils


def test_playbook_result_to_audit_dict():
    pr = PlaybookResult(
        execution_id="e1",
        playbook="t",
        objetivo="1.2.3.4",
        exitoso=True,
        mensaje="ok",
        detalles={"a": 1},
        ejecutado_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
        puede_deshacer=True,
    )
    d = playbook_result_to_audit_dict(pr)
    assert d["exito"] is True
    assert d["detalle"] == "ok"
    assert d["execution_id"] == "e1"
    assert d["puede_deshacer"] is True


def test_is_rfc1918():
    assert ip_utils.is_rfc1918("10.0.0.1") is True
    assert ip_utils.is_rfc1918("192.168.1.1") is True
    assert ip_utils.is_rfc1918("8.8.8.8") is False


def test_protected_ips(monkeypatch):
    monkeypatch.setenv("PROTECTED_IPS", "10.0.0.1, 10.0.0.2")
    assert ip_utils.is_protected_ip("10.0.0.1") is True
    assert ip_utils.is_protected_ip("8.8.8.8") is False


@pytest.mark.asyncio
async def test_block_ip_precondition_rejects_internal():
    pb = BlockIPPlaybook(mongo=None, redis_bus=None)
    can, why = await pb.check_preconditions("10.1.1.1")
    assert can is False
    assert "cuarentena" in why.lower()


@pytest.mark.asyncio
async def test_block_ip_precondition_rejects_invalid():
    pb = BlockIPPlaybook(mongo=None, redis_bus=None)
    can, _ = await pb.check_preconditions("not-an-ip")
    assert can is False


@pytest.mark.asyncio
async def test_notify_only_publishes_channels():
    rb = MagicMock()
    rb.client = MagicMock()
    rb.publish_alert = AsyncMock()
    accion = AccionPropuesta(
        tipo="notify_only",
        objetivo="a@b.com",
        descripcion="d",
        reversible=False,
        impacto="bajo",
        requiere_aprobacion=False,
    )
    ctx = {"incident_id": "inc-1", "ejecutado_by": "op"}
    pb = NotifyOnlyPlaybook(rb)
    out = await pb.execute(accion, ctx)
    assert out["exito"] is True
    assert rb.publish_alert.await_count == 2
    calls = [c.args[0] for c in rb.publish_alert.call_args_list]
    assert CHANNEL_URGENT in calls
    assert "alerts" in calls
