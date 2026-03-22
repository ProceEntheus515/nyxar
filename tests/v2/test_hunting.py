"""Tests V2: threat_hunting (QueryBuilder, HypothesisEngine, Hunter) con Claude mockeado."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from threat_hunting.hypothesis_engine import HypothesisEngine
from threat_hunting.hunter import Hunter
from threat_hunting.models import HuntingContext, Hypothesis
from threat_hunting.query_builder import QueryBuilder


@pytest.mark.v2
async def test_hipotesis_generada(mongo_client_mock, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    raw = (
        '[{"titulo":"Lateral movement","descripcion":"d","tecnica_mitre":"T1021",'
        '"prioridad":2,"queries_sugeridas":["usuarios raros"]}]'
    )
    msg = MagicMock()
    msg.text = raw
    resp = MagicMock()
    resp.content = [msg]

    async def fake_create(**kwargs):
        return resp

    eng = HypothesisEngine(mongo=mongo_client_mock, api_key="sk-test")
    with patch("threat_hunting.hypothesis_engine.anthropic.AsyncAnthropic") as m:
        client_inst = m.return_value
        client_inst.messages = MagicMock()
        client_inst.messages.create = AsyncMock(side_effect=fake_create)
        hyps = await eng.generate_hypotheses(HuntingContext(), persist=False)
    assert len(hyps) == 1
    assert hyps[0].titulo == "Lateral movement"
    assert hyps[0].queries_sugeridas


@pytest.mark.v2
async def test_hipotesis_json_valido(mongo_client_mock, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    msg = MagicMock()
    msg.text = '[{"titulo":"A","descripcion":"b","tecnica_mitre":"T1","prioridad":3,"queries_sugeridas":[]}]'
    resp = MagicMock()
    resp.content = [msg]
    eng = HypothesisEngine(mongo=mongo_client_mock, api_key="sk-test")
    with patch("threat_hunting.hypothesis_engine.anthropic.AsyncAnthropic") as m:
        m.return_value.messages.create = AsyncMock(return_value=resp)
        hyps = await eng.generate_hypotheses(HuntingContext(), persist=False)
    assert hyps and hyps[0].titulo == "A"


@pytest.mark.v2
async def test_hipotesis_json_invalido(mongo_client_mock, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    msg = MagicMock()
    msg.text = "esto no es json"
    resp = MagicMock()
    resp.content = [msg]
    eng = HypothesisEngine(mongo=mongo_client_mock, api_key="sk-test")
    with patch("threat_hunting.hypothesis_engine.anthropic.AsyncAnthropic") as m:
        m.return_value.messages.create = AsyncMock(return_value=resp)
        hyps = await eng.generate_hypotheses(HuntingContext(), persist=False)
    assert hyps == []


@pytest.mark.v2
async def test_query_builder_valida_pipeline_rechaza_out():
    qb = QueryBuilder(api_key="x")
    ok, reason = await qb._validate_pipeline([{"$match": {"x": 1}}, {"$out": "evil"}])
    assert ok is False
    assert "out" in reason.lower() or "prohibido" in reason.lower()


@pytest.mark.v2
async def test_query_builder_sin_match_rechazado():
    qb = QueryBuilder(api_key="x")
    ok, reason = await qb._validate_pipeline([{"$limit": 10}])
    assert ok is False
    assert "match" in reason.lower()


def _claude_resp(text: str) -> SimpleNamespace:
    return SimpleNamespace(content=[SimpleNamespace(text=text)])


@pytest.mark.v2
async def test_hunter_timeout(mongo_client_mock, redis_bus_fake, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    hyp = Hypothesis(
        titulo="t",
        descripcion="d",
        queries_sugeridas=["q1"],
    )

    mq_json = '{"collection": "events", "pipeline": [{"$match": {"tipo": "x"}}, {"$limit": 5}]}'
    q_resp = _claude_resp(mq_json)

    c_resp = _claude_resp(
        '{"encontrado": false, "evidencia_clave": [], "confianza": "baja", '
        '"iocs_nuevos": [], "crear_incidente": false, "justificacion": "nada"}'
    )

    qb = QueryBuilder(api_key="sk-test")
    heng = HypothesisEngine(mongo=mongo_client_mock, api_key="sk-test")
    hunter = Hunter(
        mongo=mongo_client_mock,
        query_builder=qb,
        hypothesis_engine=heng,
        redis_bus=redis_bus_fake,
    )

    q_client = MagicMock()
    q_client.messages = MagicMock()
    q_client.messages.create = AsyncMock(return_value=q_resp)
    h_client = MagicMock()
    h_client.messages = MagicMock()
    h_client.messages.create = AsyncMock(return_value=c_resp)

    # Un solo parche en el paquete anthropic: query_builder e hypothesis_engine
    # comparten la misma referencia a AsyncAnthropic; dos parches anidados la pisaban.
    with patch(
        "anthropic.AsyncAnthropic",
        side_effect=[q_client, h_client],
    ):
        with patch.object(
            hunter,
            "run_query",
            new=AsyncMock(return_value=([], "timeout")),
        ):
            session = await hunter.run_hunt(hyp, skip_critical_guard=True)
    assert session.estado == "timeout"
    assert any((a.error_o_timeout == "timeout") for a in session.detalle_queries)


@pytest.mark.v2
async def test_hunt_completo(mongo_client_mock, redis_bus_fake, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    hyp = Hypothesis(
        titulo="H1",
        descripcion="d",
        queries_sugeridas=["eventos sospechosos"],
    )

    mq_json = (
        '{"collection": "events", "pipeline": [{"$match": {"timestamp": {"$gte": "2025-01-01"}}}, {"$limit": 3}]}'
    )
    q_resp = _claude_resp(mq_json)

    c_json = (
        '{"encontrado": true, "evidencia_clave": ["ip rara"], "confianza": "media", '
        '"iocs_nuevos": ["1.2.3.4"], "crear_incidente": false, "justificacion": "ok"}'
    )
    c_resp = _claude_resp(c_json)

    qb = QueryBuilder(api_key="sk-test")
    heng = HypothesisEngine(mongo=mongo_client_mock, api_key="sk-test")
    hunter = Hunter(
        mongo=mongo_client_mock,
        query_builder=qb,
        hypothesis_engine=heng,
        redis_bus=redis_bus_fake,
    )

    q_client = MagicMock()
    q_client.messages = MagicMock()
    q_client.messages.create = AsyncMock(return_value=q_resp)
    h_client = MagicMock()
    h_client.messages = MagicMock()
    h_client.messages.create = AsyncMock(return_value=c_resp)

    with patch(
        "anthropic.AsyncAnthropic",
        side_effect=[q_client, h_client],
    ):
        with patch.object(
            hunter,
            "run_query",
            new=AsyncMock(return_value=([{"id": "e1"}], "")),
        ):
            session = await hunter.run_hunt(hyp, skip_critical_guard=True)

    assert session.estado == "completado"
    assert session.conclusion is not None
    assert session.conclusion.encontrado is True
    assert session.queries_ejecutadas >= 1
