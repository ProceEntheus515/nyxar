"""
Compresión de períodos de actividad en fingerprints (V8 U05).
Sin modelos ML externos: vector concatenado y normalizado, explicable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

import numpy as np

try:
    from motor.motor_asyncio import AsyncIOMotorDatabase
except ImportError:
    AsyncIOMotorDatabase = Any  # type: ignore


def _ensure_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _parse_event_timestamp(ev: dict[str, Any]) -> Optional[datetime]:
    ts = ev.get("timestamp")
    if ts is None:
        return None
    if isinstance(ts, datetime):
        return _ensure_utc(ts)
    if isinstance(ts, str):
        try:
            s = ts.replace("Z", "+00:00") if ts.endswith("Z") else ts
            parsed = datetime.fromisoformat(s)
            return _ensure_utc(parsed)
        except ValueError:
            return None
    return None


def _usuario_from_entity_id(entity_id: str) -> str:
    if ":" in entity_id:
        return entity_id.split(":", 1)[-1].strip() or "desconocido"
    return entity_id.strip() or "desconocido"


def _entity_tipo_from_id(entity_id: str) -> str:
    if entity_id.startswith("identity:"):
        return "identity"
    if entity_id.startswith("device:"):
        return "device"
    return "identity"


@dataclass
class BehaviorFingerprint:
    """
    Representación compacta del comportamiento de una entidad en un período.
    """

    entity_id: str
    entity_tipo: str
    period_start: datetime
    period_end: datetime
    period_type: str

    hourly_activity: list[float]
    weekday_activity: list[float]

    events_per_hour_mean: float
    events_per_hour_std: float
    bytes_per_hour_mean: float

    top_countries: dict[str, float]
    top_asns: dict[str, float]

    mean_degree: float
    mean_betweenness: float
    new_edges_per_day: float

    domain_categories: dict[str, float]
    unique_domains_per_day: float
    repeated_domain_ratio: float

    embedding: list[float] = field(default_factory=list)

    def compute_embedding(self) -> list[float]:
        """
        Vector numérico para similitud coseno (concatenación normalizada por max).
        """
        vector = (
            list(self.hourly_activity)
            + list(self.weekday_activity)
            + [
                float(self.events_per_hour_mean),
                float(self.events_per_hour_std),
                float(self.bytes_per_hour_mean),
                float(self.mean_degree),
                float(self.mean_betweenness),
                float(self.new_edges_per_day),
                float(self.unique_domains_per_day),
                float(self.repeated_domain_ratio),
            ]
        )
        arr = np.array(vector, dtype=float)
        mx = float(arr.max()) if arr.size else 0.0
        if mx > 0:
            arr = arr / mx
        self.embedding = arr.tolist()
        return self.embedding


class BehaviorCompressor:
    """
    Convierte eventos de un período en un BehaviorFingerprint.
    Soporta documentos planos (interno/externo) y time series (meta.*).
    """

    DOMAIN_CATEGORIES: dict[str, list[str]] = {
        "cdn": ["cloudflare", "akamai", "fastly", "cdn"],
        "social": ["facebook", "instagram", "twitter", "linkedin", "youtube"],
        "business": ["salesforce", "workday", "sap", "oracle"],
        "development": ["github", "stackoverflow", "npm", "docker"],
        "finance": ["banco", "bank", "afip", "sunat", "mercadopago"],
        "search": ["google", "bing", "duckduckgo"],
        "malicious": [],
    }

    async def compress_period(
        self,
        entity_id: str,
        period_start: datetime,
        period_end: datetime,
        db: AsyncIOMotorDatabase,
        *,
        mean_degree: float = 0.0,
        mean_betweenness: float = 0.0,
        new_edges_per_day: float = 0.0,
    ) -> BehaviorFingerprint:
        usuario = _usuario_from_entity_id(entity_id)
        ps = _ensure_utc(period_start)
        pe = _ensure_utc(period_end)

        q = {
            "$and": [
                {
                    "$or": [
                        {"interno.usuario": usuario},
                        {"meta.usuario": usuario},
                    ]
                },
                {"timestamp": {"$gte": ps, "$lt": pe}},
            ]
        }

        cursor = db.events.find(q)
        events = await cursor.to_list(length=None)

        if not events:
            return self._empty_fingerprint(
                entity_id,
                ps,
                pe,
                mean_degree=mean_degree,
                mean_betweenness=mean_betweenness,
                new_edges_per_day=new_edges_per_day,
            )

        hourly_raw = [0.0] * 24
        weekday_raw = [0.0] * 7
        for ev in events:
            ts = _parse_event_timestamp(ev)
            if ts is None:
                continue
            hourly_raw[ts.hour] += 1.0
            weekday_raw[ts.weekday()] += 1.0

        max_h = max(hourly_raw) or 1.0
        max_w = max(weekday_raw) or 1.0
        hourly = [h / max_h for h in hourly_raw]
        weekday = [w / max_w for w in weekday_raw]

        events_per_hour_std = float(np.std(hourly_raw)) if hourly_raw else 0.0

        period_hours = max((pe - ps).total_seconds() / 3600.0, 1e-6)
        events_per_hour_mean = len(events) / period_hours

        countries: dict[str, float] = {}
        asns: dict[str, float] = {}
        for ev in events:
            enr = ev.get("enrichment")
            if not isinstance(enr, dict):
                enr = {}
            country = enr.get("pais_origen")
            asn = enr.get("asn")
            if country:
                ck = str(country)
                countries[ck] = countries.get(ck, 0.0) + 1.0
            if asn is not None:
                ak = str(asn).strip()
                if ak:
                    asns[ak] = asns.get(ak, 0.0) + 1.0

        total = float(len(events)) or 1.0
        top_countries = {
            k: v / total
            for k, v in sorted(countries.items(), key=lambda x: -x[1])[:5]
        }
        top_asns = {k: v / total for k, v in sorted(asns.items(), key=lambda x: -x[1])[:5]}

        domain_cats = {cat: 0.0 for cat in self.DOMAIN_CATEGORIES}
        domains: list[str] = []
        for ev in events:
            ex = ev.get("externo")
            if not isinstance(ex, dict):
                ex = {}
            d = str(ex.get("valor") or "").strip()
            domains.append(d)
            enr = ev.get("enrichment")
            if isinstance(enr, dict) and enr.get("reputacion") == "malicioso":
                domain_cats["malicious"] = domain_cats.get("malicious", 0.0) + 1.0
                continue
            lower = d.lower()
            matched = False
            for cat, keywords in self.DOMAIN_CATEGORIES.items():
                if cat == "malicious":
                    continue
                if any(kw in lower for kw in keywords):
                    domain_cats[cat] = domain_cats.get(cat, 0.0) + 1.0
                    matched = True
                    break
            if not matched:
                domain_cats.setdefault("other", 0.0)
                domain_cats["other"] = domain_cats.get("other", 0.0) + 1.0

        period_days = max((pe - ps).total_seconds() / 86400.0, 1.0 / 24.0)
        unique_domains = {d for d in domains if d}
        udd = len(unique_domains) / period_days
        repeated_domain_ratio = (
            1.0 - (len(unique_domains) / total) if total > 0 else 0.0
        )

        domain_categories_norm = {k: v / total for k, v in domain_cats.items()}

        delta_days = (pe - ps).total_seconds() / 86400.0
        if delta_days <= 1.5:
            ptype = "day"
        elif delta_days <= 8:
            ptype = "week"
        else:
            ptype = "month"

        fp = BehaviorFingerprint(
            entity_id=entity_id,
            entity_tipo=_entity_tipo_from_id(entity_id),
            period_start=ps,
            period_end=pe,
            period_type=ptype,
            hourly_activity=hourly,
            weekday_activity=weekday,
            events_per_hour_mean=float(events_per_hour_mean),
            events_per_hour_std=float(events_per_hour_std),
            bytes_per_hour_mean=0.0,
            top_countries=top_countries,
            top_asns=top_asns,
            mean_degree=float(mean_degree),
            mean_betweenness=float(mean_betweenness),
            new_edges_per_day=float(new_edges_per_day),
            domain_categories=domain_categories_norm,
            unique_domains_per_day=float(udd),
            repeated_domain_ratio=float(
                max(0.0, min(1.0, repeated_domain_ratio))
            ),
        )
        fp.compute_embedding()
        return fp

    def _empty_fingerprint(
        self,
        entity_id: str,
        period_start: datetime,
        period_end: datetime,
        *,
        mean_degree: float = 0.0,
        mean_betweenness: float = 0.0,
        new_edges_per_day: float = 0.0,
    ) -> BehaviorFingerprint:
        ps = _ensure_utc(period_start)
        pe = _ensure_utc(period_end)
        empty_h = [0.0] * 24
        empty_w = [0.0] * 7
        fp = BehaviorFingerprint(
            entity_id=entity_id,
            entity_tipo=_entity_tipo_from_id(entity_id),
            period_start=ps,
            period_end=pe,
            period_type="day",
            hourly_activity=empty_h,
            weekday_activity=empty_w,
            events_per_hour_mean=0.0,
            events_per_hour_std=0.0,
            bytes_per_hour_mean=0.0,
            top_countries={},
            top_asns={},
            mean_degree=mean_degree,
            mean_betweenness=mean_betweenness,
            new_edges_per_day=new_edges_per_day,
            domain_categories={k: 0.0 for k in self.DOMAIN_CATEGORIES},
            unique_domains_per_day=0.0,
            repeated_domain_ratio=0.0,
        )
        fp.compute_embedding()
        return fp
