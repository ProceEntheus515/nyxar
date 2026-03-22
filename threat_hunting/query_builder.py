"""
Traduce queries en lenguaje natural a pipelines de agregación MongoDB validados.
"""

from __future__ import annotations

import copy
import json
import os
from typing import Any

import anthropic

from shared.logger import get_logger
from threat_hunting.models import Hypothesis, MongoQuery

logger = get_logger("threat_hunting.query_builder")

FORBIDDEN_STAGE_KEYS = frozenset({"$out", "$merge"})


CLAUDE_QUERY_PROMPT = """
Sos un experto en MongoDB Aggregation Pipeline para NYXAR.

Colecciones permitidas (campo "from" en $lookup debe ser una de estas): events, identities, incidents, honeypot_hits.

Prohibido: $out, $merge, $where, mapReduce, cualquier escritura.

Schema events (timestamp suele ser string ISO UTC en la BD):
- id, timestamp, source, tipo
- interno: ip, hostname, usuario, area
- externo: valor, tipo (ip|dominio|url|hash)
- enrichment: reputacion, fuente, categoria, tags, registrado_hace_dias, ...
- risk_score: number
- correlaciones: array de strings

Schema identities:
- id, usuario, area, hostname, risk_score, last_seen, last_alert_id, ...

Schema incidents:
- id, timestamp, patron, mitre_technique, descripcion, severidad, host_afectado, evento_original_id, detalles, estado

Schema honeypot_hits:
- id, timestamp, honeypot_name, tipo_honeypot, recurso_tocado, host_atacante, evento_original_id, descripcion, severidad

QUERY EN LENGUAJE NATURAL:
{query_natural}

Rango de tiempo a considerar en $match: últimas {horas} horas (filtrá por timestamp >= ISO adecuado).

El pipeline DEBE incluir al menos un $match como primer stage o muy al inicio, con filtro de tiempo u otro índice lógico.

Respondé SOLO con un JSON con esta forma exacta (sin markdown, sin texto extra):
{"collection": "events", "pipeline": [{"$match": {...}}, ...]}

collection debe ser una de: events, identities, incidents, honeypot_hits.
"""


def _strip_json_fences(text: str) -> str:
    clean = text.strip()
    if clean.startswith("```json"):
        clean = clean[7:].strip()
    elif clean.startswith("```"):
        clean = clean[3:].strip()
    if clean.endswith("```"):
        clean = clean[:-3].strip()
    return clean


def _contains_key_recursive(obj: Any, key: str) -> bool:
    if isinstance(obj, dict):
        if key in obj:
            return True
        return any(_contains_key_recursive(v, key) for v in obj.values())
    if isinstance(obj, list):
        return any(_contains_key_recursive(v, key) for v in obj)
    return False


def _validate_lookup_collections(
    pipeline: list[dict[str, Any]],
    allowed: frozenset[str],
) -> tuple[bool, str]:
    for stage in pipeline:
        if not isinstance(stage, dict):
            continue
        lu = stage.get("$lookup")
        if not isinstance(lu, dict):
            continue
        frm = lu.get("from")
        if frm not in allowed:
            return False, f"$lookup.from no permitido: {frm!r}"
        nested = lu.get("pipeline")
        if isinstance(nested, list):
            ok, reason = _validate_lookup_collections(nested, allowed)
            if not ok:
                return ok, reason
    return True, ""


class QueryBuilder:
    """
    Traduce hipótesis de hunting (lenguaje natural) a queries ejecutables sobre MongoDB.
    Usa Claude y valida el pipeline antes de devolverlo.
    """

    ALLOWED_COLLECTIONS = frozenset({"events", "identities", "incidents", "honeypot_hits"})
    MAX_QUERY_DURATION_SECONDS = 30
    MAX_RESULTS = 1000

    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.api_key = api_key if api_key is not None else os.getenv("ANTHROPIC_API_KEY", "")
        self.model = model or os.getenv("THREAT_HUNTING_MODEL", "claude-sonnet-4-20250514")
        try:
            self.lookback_hours = int(os.getenv("HUNTING_QUERY_LOOKBACK_HOURS", "24") or "24")
        except ValueError:
            self.lookback_hours = 24

    def _ensure_limit(self, pipeline: list[dict[str, Any]]) -> None:
        cap = self.MAX_RESULTS
        if pipeline and isinstance(pipeline[-1], dict) and "$limit" in pipeline[-1]:
            lim = pipeline[-1]["$limit"]
            try:
                n = int(lim)
            except (TypeError, ValueError):
                n = cap
            pipeline[-1]["$limit"] = max(1, min(n, cap))
        else:
            pipeline.append({"$limit": cap})

    def _validate_pipeline_core(self, pipeline: list[dict[str, Any]]) -> tuple[bool, str]:
        """
        Validaciones de seguridad: sin escritura, sin $where, $lookup acotado, al menos un $match top-level.
        """
        if not pipeline or not isinstance(pipeline, list):
            return False, "pipeline vacío o inválido"

        if not any(isinstance(s, dict) and "$match" in s for s in pipeline):
            return False, "se requiere al menos un stage $match en el pipeline principal"

        for stage in pipeline:
            if not isinstance(stage, dict) or len(stage) != 1:
                return False, "cada stage debe ser un objeto con exactamente una clave de operador"
            op = next(iter(stage))
            if op in FORBIDDEN_STAGE_KEYS:
                return False, f"stage prohibido: {op}"

        if _contains_key_recursive(pipeline, "$where"):
            return False, "prohibido usar $where"

        ok_lu, reason_lu = _validate_lookup_collections(pipeline, self.ALLOWED_COLLECTIONS)
        if not ok_lu:
            return False, reason_lu

        return True, ""

    async def _validate_pipeline(self, pipeline: list[dict[str, Any]]) -> tuple[bool, str]:
        """Misma validación que usa build_queries; expuesta para tests y herramientas."""
        return self._validate_pipeline_core(copy.deepcopy(pipeline))

    async def build_queries(self, hypothesis: Hypothesis) -> list[MongoQuery]:
        """
        Por cada query_sugerida, pide a Claude un pipeline JSON y lo valida.
        Añade $limit si falta y fuerza tope MAX_RESULTS.
        """
        out: list[MongoQuery] = []
        if not hypothesis.queries_sugeridas:
            return out
        if not self.api_key:
            logger.warning("QueryBuilder.build_queries: falta ANTHROPIC_API_KEY")
            return out

        client = anthropic.AsyncAnthropic(api_key=self.api_key)
        horas = self.lookback_hours

        for q_natural in hypothesis.queries_sugeridas:
            q_natural = (q_natural or "").strip()
            if not q_natural:
                continue
            user = CLAUDE_QUERY_PROMPT.replace("{query_natural}", q_natural).replace(
                "{horas}", str(horas)
            )
            try:
                resp = await client.messages.create(
                    model=self.model,
                    max_tokens=4096,
                    temperature=0.1,
                    system="Solo respondé el JSON pedido, sin markdown ni explicación.",
                    messages=[{"role": "user", "content": user}],
                )
                raw = resp.content[0].text if resp.content else ""
                data = json.loads(_strip_json_fences(raw))
            except Exception as e:
                logger.warning("QueryBuilder: fallo Claude para query %r: %s", q_natural[:80], e)
                continue

            if not isinstance(data, dict):
                continue
            coll = data.get("collection")
            pipeline_raw = data.get("pipeline")
            if coll not in self.ALLOWED_COLLECTIONS:
                logger.warning("QueryBuilder: colección no permitida %r", coll)
                continue
            if not isinstance(pipeline_raw, list):
                continue

            pipeline = copy.deepcopy(pipeline_raw)
            valid, reason = self._validate_pipeline_core(pipeline)
            if not valid:
                logger.warning("QueryBuilder: pipeline inválido: %s", reason)
                continue

            self._ensure_limit(pipeline)
            out.append(MongoQuery(collection=coll, pipeline=pipeline))

        return out
