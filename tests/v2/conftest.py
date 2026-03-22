"""
Fixtures compartidos V2: Mongo en memoria, Redis emulado async, utilidades de cleanup.
"""

from __future__ import annotations

import json
from collections import defaultdict
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock

import pytest
from pymongo import ReturnDocument


def _matches(doc: dict, query: dict) -> bool:
    for k, cond in query.items():
        if k == "$or":
            if not isinstance(cond, list):
                return False
            return any(_matches(doc, sub) for sub in cond if isinstance(sub, dict))
        val = doc.get(k)
        if isinstance(cond, dict):
            if "$in" in cond:
                if val not in cond["$in"]:
                    return False
            elif "$nin" in cond:
                if val in cond["$nin"]:
                    return False
            elif "$gte" in cond:
                if val is None or val < cond["$gte"]:
                    return False
            else:
                return False
        elif val != cond:
            return False
    return True


def _apply_update(doc: dict, update: dict) -> None:
    for op, fields in update.items():
        if op == "$set" and isinstance(fields, dict):
            doc.update(fields)


class MemCursor:
    def __init__(self, coll: "MemCollection", query: dict):
        self._coll = coll
        self._query = query
        self._idx = 0
        self._matched: List[dict] = [r for r in coll.rows if _matches(r, query)]

    def sort(self, *args, **kwargs):
        return self

    def limit(self, n: int):
        self._matched = self._matched[:n]
        return self

    def __aiter__(self):
        self._idx = 0
        return self

    async def __anext__(self):
        if self._idx >= len(self._matched):
            raise StopAsyncIteration
        row = dict(self._matched[self._idx])
        self._idx += 1
        return row


class MemCollection:
    def __init__(self) -> None:
        self.rows: List[dict] = []

    async def insert_one(self, doc: dict) -> MagicMock:
        d = dict(doc)
        self.rows.append(d)
        return MagicMock(inserted_id=d.get("id"))

    async def find_one(self, query: dict | None = None, sort: Any = None) -> Optional[dict]:
        query = query if query is not None else {}
        if sort:
            key, direction = sort[0]
            rev = direction == -1
            try:
                self.rows.sort(key=lambda r: r.get(key, ""), reverse=rev)
            except TypeError:
                pass
        for r in self.rows:
            if _matches(r, query):
                return dict(r)
        return None

    async def update_one(self, query: dict, update: dict) -> MagicMock:
        for r in self.rows:
            if _matches(r, query):
                _apply_update(r, update)
                return MagicMock(modified_count=1)
        return MagicMock(modified_count=0)

    async def find_one_and_update(
        self,
        filt: dict,
        update: dict,
        return_document: Any = None,
    ) -> Optional[dict]:
        for r in self.rows:
            if _matches(r, filt):
                before = dict(r)
                _apply_update(r, update)
                if return_document == ReturnDocument.BEFORE:
                    return before
                return dict(r)
        return None

    def find(self, query: dict) -> MemCursor:
        return MemCursor(self, query)

    async def count_documents(self, query: dict) -> int:
        return sum(1 for r in self.rows if _matches(r, query))

    async def create_index(self, *args, **kwargs) -> str:
        return "idx"

    def aggregate(self, pipeline: list, **kwargs) -> "MemAggregateCursor":
        return MemAggregateCursor([])


class MemAggregateCursor:
    def __init__(self, rows: List[dict]) -> None:
        self._rows = rows

    async def to_list(self, length: int) -> List[dict]:
        return list(self._rows[:length])


class MemMongoDb:
    """DB mínima para motor SOAR / approval / snapshots."""

    def __init__(self) -> None:
        self.response_proposals = MemCollection()
        self.auto_response_audit = MemCollection()
        self.audit_log = MemCollection()
        self.incidents = MemCollection()
        self.identities = MemCollection()
        self.wazuh_logons = MemCollection()
        self.playbook_quarantine_state = MemCollection()
        self.playbook_block_ip_state = MemCollection()
        self.playbook_ad_disable_state = MemCollection()
        self.notifications_log = MemCollection()
        self.events = MemCollection()
        self.hunting_hypotheses = MemCollection()
        self.hunt_sessions = MemCollection()

    def __getitem__(self, name: str) -> MemCollection:
        mapping = {
            "response_proposals": self.response_proposals,
            "auto_response_audit": self.auto_response_audit,
            "audit_log": self.audit_log,
            "incidents": self.incidents,
            "identities": self.identities,
            "wazuh_logons": self.wazuh_logons,
            "playbook_quarantine_state": self.playbook_quarantine_state,
            "playbook_block_ip_state": self.playbook_block_ip_state,
            "playbook_ad_disable_state": self.playbook_ad_disable_state,
            "notifications_log": self.notifications_log,
            "events": self.events,
            "hunting_hypotheses": self.hunting_hypotheses,
            "hunt_sessions": self.hunt_sessions,
        }
        if name not in mapping:
            c = MemCollection()
            setattr(self, name, c)
            return c
        return mapping[name]

    async def command(self, cmd: Any) -> dict:
        if cmd == "dbStats" or (isinstance(cmd, dict) and "dbStats" in cmd):
            return {"dataSize": 100, "indexSize": 50}
        return {}

    def get_collection(self, name: str, write_concern: Any = None) -> MemCollection:
        return self[name]


@pytest.fixture
def mem_db() -> MemMongoDb:
    return MemMongoDb()


@pytest.fixture
def mongo_client_mock(mem_db: MemMongoDb):
    m = MagicMock()
    m.db = mem_db

    async def ping() -> bool:
        return True

    m.ping = ping
    return m


class AsyncFakeRedisClient:
    """Redis async mínimo (strings + sets) para ingestor / resolver tests."""

    def __init__(self) -> None:
        self._kv: dict[str, str] = {}
        self._sets: dict[str, set[str]] = defaultdict(set)

    async def get(self, key: str) -> Optional[str]:
        return self._kv.get(key)

    async def set(
        self,
        key: str,
        value: str,
        ex: Optional[int] = None,
        nx: bool = False,
    ) -> bool | None:
        if nx and key in self._kv:
            return None
        self._kv[key] = value
        return True

    async def sadd(self, key: str, *members: str) -> int:
        s = self._sets[key]
        n = 0
        for m in members:
            if m not in s:
                s.add(m)
                n += 1
        return n

    async def scard(self, key: str) -> int:
        return len(self._sets.get(key, set()))

    async def sismember(self, key: str, member: str) -> bool:
        return member in self._sets.get(key, set())

    async def srem(self, key: str, *members: str) -> int:
        s = self._sets.get(key, set())
        n = 0
        for m in members:
            if m in s:
                s.discard(m)
                n += 1
        return n

    async def incr(self, key: str) -> int:
        cur = int(self._kv.get(key) or "0")
        n = cur + 1
        self._kv[key] = str(n)
        return n

    async def expire(self, key: str, _seconds: int) -> bool:
        return key in self._kv

    async def delete(self, key: str) -> int:
        if key in self._kv:
            del self._kv[key]
            return 1
        return 0

    async def exists(self, key: str) -> int:
        return 1 if key in self._kv else 0

    async def ping(self) -> bool:
        return True

    async def info(self, section: str | None = None) -> dict:
        return {"used_memory_human": "1M", "connected_clients": 1}


@pytest.fixture
async def redis_bus_fake():
    from shared.redis_bus import RedisBus

    bus = RedisBus()
    fake = AsyncFakeRedisClient()
    bus.client = fake

    async def fake_connect() -> None:
        bus.client = fake

    bus.connect = fake_connect

    async def cache_get(key: str):
        raw = await fake.get(key)
        if raw:
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                return None
        return None

    async def cache_set(key: str, value: dict, ttl: int) -> None:
        await fake.set(key, json.dumps(value), ex=ttl)

    async def cache_delete(key: str) -> None:
        await fake.delete(key)

    async def cache_exists(key: str) -> bool:
        return bool(await fake.exists(key))

    bus.cache_get = cache_get
    bus.cache_set = cache_set
    bus.cache_delete = cache_delete
    bus.cache_exists = cache_exists

    yield bus


@pytest.fixture(autouse=False)
def misp_env(monkeypatch):
    monkeypatch.setenv("MISP_URL", "https://misp.test")
    monkeypatch.setenv("MISP_API_KEY", "test-key-hex")
    monkeypatch.setenv("MISP_VERIFY_SSL", "false")
