"""Tests HypothesisEngine y serialización de contexto (sin llamada de red real)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from threat_hunting.context_builder import build_hunting_context, hunting_context_to_prompt_chunks
from threat_hunting.hypothesis_engine import HypothesisEngine
from threat_hunting.models import HuntingContext, Hypothesis


def test_hunting_context_to_prompt_chunks_includes_keys():
    ctx = HuntingContext(
        estadisticas_24h={"eventos_totales_aprox": 1},
        threat_intel_resumen="MISP: 0 hits",
        incidentes_semana=[{"id": "i1"}],
        iocs_sin_alerta=[{"valor": "1.1.1.1", "tipo": "ip", "frecuencia": 3}],
        identidades_riesgo_suave=[{"id": "h1", "risk_score": 20}],
    )
    chunks = hunting_context_to_prompt_chunks(ctx)
    assert "eventos_totales_aprox" in chunks["context"]
    assert chunks["threat_intel"] == "MISP: 0 hits"
    assert "i1" in chunks["recent_incidents"]


@pytest.mark.asyncio
async def test_build_hunting_context_tolerates_empty_db():
    def empty_agg_cursor():
        c = MagicMock()
        c.to_list = AsyncMock(return_value=[])
        return c

    events = MagicMock()
    events.aggregate = MagicMock(side_effect=[empty_agg_cursor(), empty_agg_cursor()])
    events.distinct = AsyncMock(return_value=[])

    inc_cursor = MagicMock()
    inc_cursor.to_list = AsyncMock(return_value=[])
    inc_lim = MagicMock()
    inc_lim.limit = MagicMock(return_value=inc_cursor)
    incidents = MagicMock()
    incidents.find = MagicMock(return_value=inc_lim)

    id_cursor = MagicMock()
    id_cursor.to_list = AsyncMock(return_value=[])
    id_lim = MagicMock()
    id_lim.limit = MagicMock(return_value=id_cursor)
    id_sort = MagicMock()
    id_sort.sort = MagicMock(return_value=id_lim)
    identities = MagicMock()
    identities.find = MagicMock(return_value=id_sort)

    class DB:
        def __getitem__(self, name):
            if name == "events":
                return events
            if name == "incidents":
                return incidents
            if name == "identities":
                return identities
            return MagicMock()

    mongo = MagicMock()
    mongo.db = DB()

    with patch("threat_hunting.context_builder.MongoClient", return_value=mongo):
        with patch("threat_hunting.context_builder.RedisBus") as rb_cls:
            rb = MagicMock()
            rb.client = None
            rb_cls.return_value = rb
            ctx = await build_hunting_context(mongo=mongo)
    assert ctx.estadisticas_24h.get("ventana") == "24h"


@pytest.mark.asyncio
async def test_generate_hypotheses_parses_and_skips_duplicates():
    llm_json = """```json
[
  {"titulo": "H1", "descripcion": "d", "tecnica_mitre": "T1071", "prioridad": 4, "queries_sugeridas": ["q1"]},
  {"titulo": "h1", "descripcion": "dup", "tecnica_mitre": "T1", "prioridad": 2, "queries_sugeridas": []}
]
```"""

    msg = MagicMock()
    msg.content = [MagicMock(text=llm_json)]
    create_mock = AsyncMock(return_value=msg)
    anthropic_client = MagicMock()
    anthropic_client.messages = MagicMock(create=create_mock)

    hypotheses_coll = MagicMock()
    hypotheses_coll.count_documents = AsyncMock(return_value=0)
    hypotheses_coll.insert_one = AsyncMock()

    class DB:
        def __getitem__(self, name):
            if name == "hunting_hypotheses":
                return hypotheses_coll
            return MagicMock()

    mongo = MagicMock()
    mongo.db = DB()

    engine = HypothesisEngine(mongo=mongo, api_key="k", model="test-model")

    with patch("threat_hunting.hypothesis_engine.anthropic.AsyncAnthropic", return_value=anthropic_client):
        out = await engine.generate_hypotheses(HuntingContext(), persist=True)

    assert len(out) == 1
    assert out[0].titulo == "H1"
    assert out[0].prioridad == 4
    create_mock.assert_awaited_once()
    hypotheses_coll.insert_one.assert_awaited_once()


@pytest.mark.asyncio
async def test_conclude_hunt_maps_findings():
    llm_json = """{
  "encontrado": true,
  "confianza": "media",
  "evidencia_clave": ["e1"],
  "iocs_nuevos": ["10.0.0.1"],
  "crear_incidente": false,
  "justificacion": "ok"
}"""
    msg = MagicMock()
    msg.content = [MagicMock(text=llm_json)]
    create_mock = AsyncMock(return_value=msg)
    anthropic_client = MagicMock()
    anthropic_client.messages = MagicMock(create=create_mock)

    hyp = Hypothesis(id="hyp_x", titulo="t", descripcion="d")
    engine = HypothesisEngine(mongo=None, api_key="k", model="m")

    with patch("threat_hunting.hypothesis_engine.anthropic.AsyncAnthropic", return_value=anthropic_client):
        concl = await engine.conclude_hunt(hyp, [{"foo": 1}])

    assert concl.hypothesis_id == "hyp_x"
    assert concl.encontrado is True
    assert concl.confianza == "media"
    assert concl.evidencia == [{"descripcion": "e1"}]
    assert concl.iocs_nuevos == ["10.0.0.1"]
    assert concl.crear_incidente is False
