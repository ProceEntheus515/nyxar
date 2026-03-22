"""Tests ApprovalManager y AuditLogger (PROMPTS_V2)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from auto_response.approval import ApprovalManager, _pending_sort_key
from auto_response.audit import AuditLogger, _safe_payload_fragment


def test_safe_payload_fragment_strips_secrets():
    p = {
        "objetivo": "1.2.3.4",
        "token": "secret",
        "detalles": {"password": "x", "ok": 1},
    }
    out = _safe_payload_fragment(p)
    assert out.get("objetivo") == "1.2.3.4"
    assert "token" not in out
    assert "password" not in (out.get("detalles") or {})


def test_pending_sort_key_urgency():
    hi = {"plan": {"urgencia": "inmediata"}, "creado_at": "2025-01-02T00:00:00+00:00"}
    lo = {"plan": {"urgencia": "proximo_dia"}, "creado_at": "2025-01-01T00:00:00+00:00"}
    assert _pending_sort_key(hi) < _pending_sort_key(lo)


@pytest.mark.asyncio
async def test_approval_manager_approve_updates_and_redis():
    proposals = MagicMock()
    proposals.find_one = AsyncMock(
        return_value={
            "id": "p1",
            "estado": "pendiente_aprobacion",
            "incident_id": "INC-1",
            "plan": {"playbook_nombre": "pb", "urgencia": "proxima_hora"},
        }
    )
    proposals.update_one = AsyncMock(
        return_value=MagicMock(modified_count=1)
    )
    incidents = MagicMock()
    incidents.find_one = AsyncMock(return_value=None)
    identities = MagicMock()
    audit_coll = MagicMock()
    audit_coll.insert_one = AsyncMock(return_value=MagicMock(inserted_id="oid"))

    class DB:
        def __getitem__(self, name):
            if name == "response_proposals":
                return proposals
            if name == "incidents":
                return incidents
            if name == "identities":
                return identities
            if name == "audit_log":
                return audit_coll
            return MagicMock()

        def get_collection(self, name, write_concern=None):
            return audit_coll

    mongo = MagicMock()
    mongo.db = DB()
    redis = MagicMock()
    redis.client = MagicMock()
    redis.publish_alert = AsyncMock()
    al = AuditLogger(mongo)
    am = ApprovalManager(mongo, redis, al)
    ok = await am.approve("p1", "operator1", "ok")
    assert ok is True
    redis.publish_alert.assert_awaited_once()
    assert redis.publish_alert.call_args[0][0] == "approvals:ready"


@pytest.mark.asyncio
async def test_approval_auto_expire_count():
    docs = [
        {
            "id": "old",
            "estado": "pendiente_aprobacion",
            "creado_at": "2000-01-01T00:00:00+00:00",
            "incident_id": "I1",
            "plan": {"playbook_nombre": "x"},
        },
    ]

    class Cursor:
        def __init__(self, items):
            self._items = items

        def __aiter__(self):
            self._i = 0
            return self

        async def __anext__(self):
            if self._i >= len(self._items):
                raise StopAsyncIteration
            x = self._items[self._i]
            self._i += 1
            return x

    proposals = MagicMock()
    proposals.find = MagicMock(side_effect=lambda q: Cursor(list(docs)))
    proposals.update_one = AsyncMock(return_value=MagicMock(modified_count=1))

    audit_coll = MagicMock()
    audit_coll.insert_one = AsyncMock(return_value=MagicMock(inserted_id="a"))

    class DB:
        def __getitem__(self, name):
            if name == "response_proposals":
                return proposals
            if name == "incidents":
                m = MagicMock()
                m.find_one = AsyncMock(return_value=None)
                return m
            if name == "audit_log":
                return audit_coll
            return MagicMock()

        def get_collection(self, name, write_concern=None):
            return audit_coll

    mongo = MagicMock()
    mongo.db = DB()
    am = ApprovalManager(mongo, None, AuditLogger(mongo))
    with patch.dict("os.environ", {"APPROVAL_TIMEOUT": "1"}, clear=False):
        n = await am.auto_expire()
    assert n == 1
