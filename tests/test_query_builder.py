"""Validación estática de pipelines (QueryBuilder) sin Claude."""

import pytest

from threat_hunting.query_builder import QueryBuilder


@pytest.mark.asyncio
async def test_validate_pipeline_rejects_out():
    qb = QueryBuilder()
    pipe = [{"$match": {"source": "dns"}}, {"$out": "evil"}]
    ok, reason = await qb._validate_pipeline(pipe)
    assert ok is False
    assert "prohibido" in reason.lower() or "out" in reason.lower()


@pytest.mark.asyncio
async def test_validate_pipeline_rejects_where():
    qb = QueryBuilder()
    pipe = [{"$match": {"$where": "1==1"}}]
    ok, reason = await qb._validate_pipeline(pipe)
    assert ok is False
    assert "where" in reason.lower()


@pytest.mark.asyncio
async def test_validate_pipeline_rejects_lookup_from_unknown():
    qb = QueryBuilder()
    pipe = [
        {"$match": {"a": 1}},
        {"$lookup": {"from": "users", "localField": "x", "foreignField": "y", "as": "z"}},
    ]
    ok, reason = await qb._validate_pipeline(pipe)
    assert ok is False
    assert "lookup" in reason.lower() or "permitido" in reason.lower()


@pytest.mark.asyncio
async def test_validate_pipeline_accepts_safe_events():
    qb = QueryBuilder()
    pipe = [
        {"$match": {"timestamp": {"$gte": "2025-01-01T00:00:00Z"}}},
        {"$group": {"_id": "$source", "n": {"$sum": 1}}},
    ]
    ok, reason = await qb._validate_pipeline(pipe)
    assert ok is True
    assert reason == ""


def test_ensure_limit_caps():
    qb = QueryBuilder()
    p = [{"$match": {}}]
    qb._ensure_limit(p)
    assert p[-1] == {"$limit": QueryBuilder.MAX_RESULTS}

    p2 = [{"$match": {}}, {"$limit": 50000}]
    qb._ensure_limit(p2)
    assert p2[-1]["$limit"] == QueryBuilder.MAX_RESULTS
