"""Tests unitarios del conector AD (sin LDAP real)."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from ad_connector.client import (
    ADClient,
    filetime_to_datetime,
    generalized_time_utc,
)
from ad_connector.identity_sync import IdentitySync


class _EmptyCursor:
    def __aiter__(self):
        return self

    async def __anext__(self):
        raise StopAsyncIteration


@pytest.mark.unit
def test_filetime_to_datetime_none():
    assert filetime_to_datetime(None) is None


@pytest.mark.unit
def test_filetime_to_datetime_zero():
    assert filetime_to_datetime(0) is None


@pytest.mark.unit
def test_filetime_to_datetime_known():
    # 1 hora despues del epoch FILETIME (100-ns ticks)
    ticks = 60 * 60 * 10_000_000
    dt = filetime_to_datetime(ticks)
    assert dt is not None
    assert dt.tzinfo == timezone.utc
    assert dt.hour == 1


@pytest.mark.unit
def test_generalized_time_utc_naive():
    dt = datetime(2024, 3, 15, 12, 30, 45)
    s = generalized_time_utc(dt)
    assert s == "20240315123045.0Z"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_get_logged_on_users_from_wazuh_logons():
    mongo = MagicMock()
    mongo.db = MagicMock()

    async def fake_aggregate(_pipe):
        yield {
            "_id": "10.0.0.5",
            "usuario": "ana.perez",
            "hostname": "PC-01",
            "desde": datetime(2024, 1, 1, tzinfo=timezone.utc),
        }

    coll = MagicMock()
    coll.aggregate = lambda p: fake_aggregate(p)
    mongo.db.wazuh_logons = coll

    client = ADClient(mongo_client=mongo)
    rows = await client.get_logged_on_users()
    assert len(rows) == 1
    assert rows[0]["ip"] == "10.0.0.5"
    assert rows[0]["usuario"] == "ana.perez"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_identity_sync_upsert_no_pisa_risk_score_en_set():
    captured = {}

    async def fake_update_one(filtro, update, upsert=False):
        captured["update"] = update
        r = MagicMock()
        r.upserted_id = "x"
        r.matched_count = 0
        r.modified_count = 0
        return r

    col = MagicMock()
    col.update_one = fake_update_one
    col.find = MagicMock(return_value=_EmptyCursor())

    mongo = MagicMock()
    mongo.db = MagicMock()
    mongo.db.identities = col

    syncer = IdentitySync(mongo_client=mongo, redis_bus=None)
    ad = MagicMock(spec=ADClient)
    ad.get_all_users = AsyncMock(
        return_value=[
            {
                "sAMAccountName": "jdoe",
                "displayName": "John Doe",
                "department": "IT",
                "mail": "j@x.com",
                "title": "Dev",
                "manager": None,
                "memberOf": ["CN=Domain Users,DC=x,DC=com"],
                "lastLogon": 0,
                "userWorkstations": None,
                "whenCreated": datetime(2020, 1, 1, tzinfo=timezone.utc),
                "whenChanged": None,
                "distinguishedName": "CN=jdoe,OU=Users,DC=x,DC=com",
            }
        ]
    )
    ad.get_computers = AsyncMock(return_value=[])
    ad.get_groups = AsyncMock(return_value=[])

    stats = await syncer.full_sync(ad)
    assert stats["sincronizados"] >= 1
    assert "risk_score" not in captured["update"]["$set"]
    assert "baseline" not in captured["update"]["$set"]
    assert captured["update"]["$setOnInsert"]["risk_score"] == 0


@pytest.mark.unit
def test_user_ldap_filter_balance():
    DISABLED_UAC_BIT = 2
    filt = (
        "(&(objectClass=user)(objectCategory=person)"
        "(!(userAccountControl:1.2.840.113556.1.4.803:=%s)))"
    ) % DISABLED_UAC_BIT
    assert filt.count("(") == filt.count(")")
