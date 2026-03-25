"""
Índice de fingerprints en MongoDB y búsqueda por similitud coseno (V8 U05).
Retención: como mucho 52 fingerprints semanales por entidad (1 año).
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import numpy as np

from nyxar.deep_memory.compressor import BehaviorFingerprint

try:
    from motor.motor_asyncio import AsyncIOMotorDatabase
except ImportError:
    AsyncIOMotorDatabase = Any  # type: ignore

try:
    from shared.logger import get_logger

    logger = get_logger("deep_memory.indexer")
except ImportError:
    logger = logging.getLogger("nyxar.deep_memory.indexer")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _ensure_utc(dt: Any) -> Optional[datetime]:
    if dt is None:
        return None
    if isinstance(dt, datetime):
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    if isinstance(dt, str):
        try:
            s = dt.replace("Z", "+00:00") if dt.endswith("Z") else dt
            return _ensure_utc(datetime.fromisoformat(s))
        except ValueError:
            return None
    return None


MAX_WEEKLY_FINGERPRINTS_PER_ENTITY = 52


class FingerprintIndexer:
    """
    Persistencia y búsqueda por similitud sobre behavior_fingerprints.
    """

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self.db = db
        self._cache: dict[str, list[dict[str, Any]]] = {}

    async def store(self, fingerprint: BehaviorFingerprint) -> None:
        """Persiste un fingerprint; aplica retención máxima por entidad."""
        ps = fingerprint.period_start
        if ps.tzinfo is None:
            ps = ps.replace(tzinfo=timezone.utc)
        doc_id = f"{fingerprint.entity_id}:{ps.isoformat()}"
        doc: dict[str, Any] = {
            "_id": doc_id,
            "entity_id": fingerprint.entity_id,
            "entity_tipo": fingerprint.entity_tipo,
            "period_start": fingerprint.period_start,
            "period_end": fingerprint.period_end,
            "period_type": fingerprint.period_type,
            "embedding": fingerprint.embedding,
            "domain_categories": fingerprint.domain_categories,
            "hourly_activity": fingerprint.hourly_activity,
            "weekday_activity": fingerprint.weekday_activity,
            "top_countries": fingerprint.top_countries,
            "top_asns": fingerprint.top_asns,
            "unique_domains_per_day": fingerprint.unique_domains_per_day,
            "events_per_hour_mean": fingerprint.events_per_hour_mean,
            "events_per_hour_std": fingerprint.events_per_hour_std,
            "created_at": _utcnow(),
        }
        await self.db.behavior_fingerprints.replace_one(
            {"_id": doc["_id"]}, doc, upsert=True
        )
        await self._enforce_weekly_retention(fingerprint.entity_id)

    async def _enforce_weekly_retention(self, entity_id: str) -> None:
        """
        Como mucho 52 fingerprints por entidad (equivalente a 1 año de ventanas semanales).
        Elimina los más antiguos por period_start.
        """
        cur = self.db.behavior_fingerprints.find({"entity_id": entity_id}).sort(
            "period_start", 1
        )
        docs = await cur.to_list(length=None)
        if len(docs) <= MAX_WEEKLY_FINGERPRINTS_PER_ENTITY:
            return
        to_drop = docs[: len(docs) - MAX_WEEKLY_FINGERPRINTS_PER_ENTITY]
        for d in to_drop:
            await self.db.behavior_fingerprints.delete_one({"_id": d["_id"]})

    async def find_similar(
        self,
        current_fingerprint: BehaviorFingerprint,
        top_k: int = 5,
        min_similarity: float = 0.85,
        *,
        entity_risk_score: Optional[int] = None,
        risk_threshold: int = 40,
    ) -> list[dict[str, Any]]:
        """
        Similitud coseno entre embeddings. Si entity_risk_score <= risk_threshold, no busca (regla V8).
        """
        if entity_risk_score is not None and entity_risk_score <= risk_threshold:
            return []

        entity_id = current_fingerprint.entity_id
        current_emb = np.array(current_fingerprint.embedding, dtype=float)
        if current_emb.size == 0:
            return []

        historical = await self.db.behavior_fingerprints.find(
            {
                "entity_id": entity_id,
                "period_end": {"$lt": _utcnow()},
            }
        ).to_list(length=500)

        if not historical:
            return []

        similarities: list[dict[str, Any]] = []
        cur_ps = current_fingerprint.period_start
        if cur_ps.tzinfo is None:
            cur_ps = cur_ps.replace(tzinfo=timezone.utc)

        for hist in historical:
            h_ps = hist.get("period_start")
            if isinstance(h_ps, datetime) and isinstance(cur_ps, datetime):
                a = h_ps if h_ps.tzinfo else h_ps.replace(tzinfo=timezone.utc)
                b = cur_ps
                if abs((a - b).total_seconds()) < 1.0:
                    continue

            hist_emb = np.array(hist.get("embedding") or [], dtype=float)
            if hist_emb.size != current_emb.size or hist_emb.size == 0:
                continue

            dot = float(np.dot(current_emb, hist_emb))
            norm = float(np.linalg.norm(current_emb) * np.linalg.norm(hist_emb))
            similarity = dot / norm if norm > 0 else 0.0

            if similarity >= min_similarity:
                similarities.append(
                    {
                        "fingerprint_id": hist.get("_id"),
                        "period_start": hist.get("period_start"),
                        "period_end": hist.get("period_end"),
                        "similarity": round(float(similarity), 4),
                    }
                )

        similarities.sort(key=lambda x: -float(x["similarity"]))
        return similarities[:top_k]

    async def find_precursor_patterns(
        self,
        incident_date: datetime,
        entity_id: str,
        lookahead_days: int = 14,
    ) -> Optional[dict[str, Any]]:
        """
        Marca el fingerprint precursor antes de un incidente (ventana configurable).
        Devuelve el documento Mongo o None.
        """
        inc = _ensure_utc(incident_date)
        if inc is None:
            return None

        precursor_start = inc - timedelta(days=lookahead_days)
        precursor_end = inc - timedelta(days=1)

        precursor_doc = await self.db.behavior_fingerprints.find_one(
            {
                "entity_id": entity_id,
                "period_start": {"$gte": precursor_start},
                "period_end": {"$lte": precursor_end},
            }
        )

        if precursor_doc:
            await self.db.behavior_fingerprints.update_one(
                {"_id": precursor_doc["_id"]},
                {
                    "$set": {
                        "is_incident_precursor": True,
                        "incident_date": inc,
                    }
                },
            )

        return precursor_doc
