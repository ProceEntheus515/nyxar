"""
Muestreo estratificado del stream para el Unknown Detector (V8 U08).
Compatible con eventos con `source`/`interno` o `meta.*` (time series).
"""

from __future__ import annotations

import logging
import random
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

try:
    from motor.motor_asyncio import AsyncIOMotorDatabase
except ImportError:
    AsyncIOMotorDatabase = Any  # type: ignore

try:
    from shared.logger import get_logger

    logger = get_logger("unknown_detector.sampler")
except ImportError:
    logger = logging.getLogger("nyxar.unknown_detector.sampler")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _parse_ts(ts: Any) -> Optional[datetime]:
    if ts is None:
        return None
    if isinstance(ts, datetime):
        if ts.tzinfo is None:
            return ts.replace(tzinfo=timezone.utc)
        return ts.astimezone(timezone.utc)
    if isinstance(ts, str):
        try:
            s = ts.replace("Z", "+00:00") if ts.endswith("Z") else ts
            return _parse_ts(datetime.fromisoformat(s))
        except ValueError:
            return None
    return None


class StreamSampler:
    """
    Muestra representativa del stream: estratificada por fuente y sesgada a interés.
    """

    SAMPLE_SIZE = 200
    MAX_TOKENS_APPROX = 8000

    async def sample(
        self,
        db: AsyncIOMotorDatabase,
        hours_back: int = 6,
        exclude_known_incidents: bool = True,
    ) -> list[dict[str, Any]]:
        cutoff = _utcnow() - timedelta(hours=hours_back)

        exclude_ids: list[str] = []
        if exclude_known_incidents:
            exclude_ids = await self._get_open_incident_event_ids(db)

        strata_config: dict[str, dict[str, Any]] = {
            "dns": {"source": "dns", "fraction": 0.40},
            "proxy": {"source": "proxy", "fraction": 0.20},
            "firewall": {"source": "firewall", "fraction": 0.20},
            "other": {"source": "__wazuh_endpoint__", "fraction": 0.20},
        }

        sample: list[dict[str, Any]] = []

        for _name, config in strata_config.items():
            n = max(1, int(self.SAMPLE_SIZE * float(config["fraction"])))
            match_q = self._match_for_stratum(cutoff, config["source"], exclude_ids)
            stratum_events = await self._draw_stratum(db, match_q, n)
            scored = [(ev, self._interest_score(ev)) for ev in stratum_events]
            scored.sort(key=lambda x: -x[1])
            sample.extend([ev for ev, _ in scored[:n]])

        random.shuffle(sample)
        return sample[: self.SAMPLE_SIZE]

    def _match_for_stratum(
        self,
        cutoff: datetime,
        source: Optional[str],
        exclude_ids: list[str],
    ) -> dict[str, Any]:
        parts: list[dict[str, Any]] = [
            {"timestamp": {"$gte": cutoff}},
            {"$nor": [{"enrichment.reputacion": "malicioso"}]},
        ]
        if source == "__wazuh_endpoint__":
            parts.append(
                {
                    "$or": [
                        {"source": {"$in": ["wazuh", "endpoint"]}},
                        {"meta.source": {"$in": ["wazuh", "endpoint"]}},
                    ]
                }
            )
        elif source is not None:
            parts.append(
                {
                    "$or": [
                        {"source": source},
                        {"meta.source": source},
                    ]
                }
            )

        if exclude_ids:
            parts.append({"id": {"$nin": exclude_ids}})

        if len(parts) == 1:
            return parts[0]
        return {"$and": parts}

    async def _draw_stratum(
        self,
        db: AsyncIOMotorDatabase,
        match_q: dict[str, Any],
        target_n: int,
    ) -> list[dict[str, Any]]:
        sample_size = min(max(target_n * 3, 20), 500)
        project = {
            "$project": {
                "id": {"$ifNull": ["$id", "$_id"]},
                "timestamp": 1,
                "source": {"$ifNull": ["$source", "$meta.source"]},
                "usuario": {"$ifNull": ["$interno.usuario", "$meta.usuario"]},
                "area": {"$ifNull": ["$interno.area", "$meta.area"]},
                "valor_externo": "$externo.valor",
                "tipo_externo": "$externo.tipo",
                "reputacion": "$enrichment.reputacion",
                "risk_score": "$risk_score",
            }
        }
        pipeline = [
            {"$match": match_q},
            {"$sample": {"size": sample_size}},
            project,
        ]
        try:
            cursor = db.events.aggregate(pipeline)
            return await cursor.to_list(length=sample_size)
        except Exception as e:
            logger.warning("aggregate $sample fallo (%s), fallback find", e)
            return await self._fallback_draw(db, match_q, sample_size)

    async def _fallback_draw(
        self,
        db: AsyncIOMotorDatabase,
        match_q: dict[str, Any],
        limit: int,
    ) -> list[dict[str, Any]]:
        cursor = db.events.find(match_q).sort("timestamp", -1).limit(limit)
        raw = await cursor.to_list(length=limit)
        return [_normalize_event_doc(d) for d in raw]


def _normalize_event_doc(doc: dict[str, Any]) -> dict[str, Any]:
    meta = doc.get("meta") or {}
    interno = doc.get("interno") or {}
    ex = doc.get("externo") or {}
    enr = doc.get("enrichment") or {}
    rep = enr.get("reputacion") if isinstance(enr, dict) else None
    return {
        "id": doc.get("id") or doc.get("_id"),
        "timestamp": doc.get("timestamp"),
        "source": doc.get("source") or meta.get("source"),
        "usuario": interno.get("usuario") or meta.get("usuario"),
        "area": interno.get("area") or meta.get("area"),
        "valor_externo": ex.get("valor") if isinstance(ex, dict) else None,
        "tipo_externo": ex.get("tipo") if isinstance(ex, dict) else None,
        "reputacion": rep,
        "risk_score": doc.get("risk_score"),
    }

    def _interest_score(self, event: dict[str, Any]) -> float:
        score = 0.0
        if event.get("reputacion") == "desconocido":
            score += 0.5

        ts = _parse_ts(event.get("timestamp"))
        if ts:
            h = ts.hour
            if h < 7 or h > 21:
                score += 0.3
            if ts.weekday() >= 5:
                score += 0.2

        rs = event.get("risk_score", 0) or 0
        try:
            rsi = int(rs)
        except (TypeError, ValueError):
            rsi = 0
        if 15 < rsi < 50:
            score += 0.3

        return score

    async def _get_open_incident_event_ids(self, db: AsyncIOMotorDatabase) -> list[str]:
        incidents = await db.incidents.find(
            {"estado": "abierto"},
            {"eventos_ids": 1},
        ).to_list(100)

        ids: list[str] = []
        for inc in incidents:
            raw = inc.get("eventos_ids") or []
            if isinstance(raw, list):
                ids.extend(str(x) for x in raw if x)
        return ids
