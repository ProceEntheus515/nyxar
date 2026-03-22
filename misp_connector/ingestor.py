"""
Ingesta de IOCs desde MISP hacia blocklists Redis del enricher.
"""

from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone
from typing import Any, Optional

from shared.logger import get_logger
from shared.redis_bus import RedisBus

from misp_connector.client import MISPClient

logger = get_logger("misp_connector.ingestor")

MISP_ATTRIBUTE_TYPES = [
    "ip-src",
    "ip-dst",
    "domain",
    "hostname",
    "md5",
    "sha1",
    "sha256",
    "sha512",
    "url",
    "email-src",
    "email-dst",
]

META_TTL_S = 172800
KEY_LAST_SYNC = "misp:last_sync"


def _normalize_ioc_value(misp_type: str, raw: Any) -> Optional[str]:
    if raw is None:
        return None
    if isinstance(raw, list):
        raw = raw[0] if raw else None
    if raw is None:
        return None
    v = str(raw).strip()
    if not v:
        return None
    t = misp_type.lower()
    if t in ("md5", "sha1", "sha256", "sha512"):
        return v.lower()
    if t in ("domain", "hostname", "email-src", "email-dst"):
        return v.lower()
    return v


def _blocklist_short_name(misp_type: str) -> Optional[str]:
    t = misp_type.lower()
    if t in ("ip-src", "ip-dst"):
        return "misp_ips"
    if t in ("domain", "hostname", "email-src", "email-dst"):
        return "misp_domains"
    if t in ("md5", "sha1", "sha256", "sha512"):
        return "misp_hashes"
    if t == "url":
        return "misp_urls"
    return None


def _tags_from_misp_obj(obj: dict) -> list[str]:
    out: list[str] = []
    tag = obj.get("Tag")
    if not isinstance(tag, list):
        return out
    for item in tag:
        if isinstance(item, dict):
            name = item.get("name") or item.get("Name")
            if name:
                out.append(str(name))
        elif isinstance(item, str):
            out.append(item)
    return out


def _org_name_from_event(event: dict | None) -> str:
    if not event:
        return ""
    for key in ("Orgc", "orgc", "Org", "org"):
        blk = event.get(key)
        if isinstance(blk, dict):
            n = blk.get("name") or blk.get("Name")
            if n:
                return str(n)
    return ""


class MISPIngestor:
    """
    Consume IOCs de MISP y los carga en las blocklists de Redis del enricher.
    """

    SYNC_INTERVAL = 300

    def __init__(self, redis_bus: RedisBus | None = None) -> None:
        self.redis_bus = redis_bus or RedisBus()

    def _map_threat_level(self, level_id: int) -> str:
        if level_id <= 2:
            return "malicioso"
        return "sospechoso"

    def _threat_level_id(self, event: dict | None, attribute: dict) -> int:
        if event:
            raw = event.get("threat_level_id")
            if raw is not None:
                try:
                    return int(raw)
                except (TypeError, ValueError):
                    pass
        return 4

    async def get_context_for_ioc(self, valor: str, redis_bus: RedisBus) -> Optional[dict]:
        return await redis_bus.cache_get(f"misp:meta:{valor}")

    async def _ingest_attributes(
        self,
        rows: list[dict],
    ) -> tuple[int, int, int, set[str]]:
        """
        Retorna (nuevos_en_set, meta_actualizados_o_ttl, total_procesados, tipos_distintos).
        """
        r = self.redis_bus.client
        if not r:
            return 0, 0, 0, set()

        nuevos = 0
        meta_updates = 0
        tipos: set[str] = set()

        for row in rows:
            attr = row.get("attribute") or {}
            event = row.get("event")
            if not isinstance(attr, dict):
                continue
            misp_type = str(attr.get("type") or "").lower()
            if not misp_type:
                continue
            tipos.add(misp_type)

            valor = _normalize_ioc_value(misp_type, attr.get("value"))
            if not valor:
                continue

            lista = _blocklist_short_name(misp_type)
            if not lista:
                continue

            key_set = f"blocklist:{lista}"
            meta_key = f"misp:meta:{valor}"

            added = await r.sadd(key_set, valor)
            if added > 0:
                nuevos += 1

            new_tl = self._threat_level_id(event if isinstance(event, dict) else None, attr)
            existing = await self.redis_bus.cache_get(meta_key)

            if existing and isinstance(existing, dict):
                try:
                    old_tl = int(existing.get("threat_level_id", 4))
                except (TypeError, ValueError):
                    old_tl = 4
                if new_tl > old_tl:
                    await self.redis_bus.cache_expire(meta_key, META_TTL_S)
                    meta_updates += 1
                    continue

            tags_a = _tags_from_misp_obj(attr)
            tags_e = _tags_from_misp_obj(event) if isinstance(event, dict) else []
            merged_tags = list(dict.fromkeys(tags_a + tags_e))

            event_name = "MISP IOC"
            if isinstance(event, dict) and event.get("info"):
                event_name = str(event["info"])

            payload = {
                "event_name": event_name,
                "threat_level_id": new_tl,
                "tags": merged_tags[:50],
                "org_name": _org_name_from_event(event if isinstance(event, dict) else None),
                "reputacion": self._map_threat_level(new_tl),
                "misp_type": misp_type,
            }
            await self.redis_bus.cache_set(meta_key, payload, META_TTL_S)
            meta_updates += 1

        total = len(rows)
        return nuevos, meta_updates, total, tipos

    async def sync_once(self, client: MISPClient) -> dict[str, Any]:
        t0 = time.perf_counter()
        await self.redis_bus.connect()
        r = self.redis_bus.client
        if not r:
            logger.error("Redis no disponible para ingestor MISP")
            return {
                "nuevos": 0,
                "actualizados": 0,
                "total": 0,
                "tipos_distintos": 0,
                "latencia_ms": 0.0,
            }

        raw_last = await r.get(KEY_LAST_SYNC)
        publish_ts: int | None = None
        if raw_last:
            try:
                s = raw_last if isinstance(raw_last, str) else str(raw_last)
                dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                publish_ts = int(dt.timestamp())
            except (TypeError, ValueError):
                publish_ts = None

        if publish_ts is not None:
            rows = await client.get_attributes(
                type_filter=MISP_ATTRIBUTE_TYPES,
                limit=5000,
                publish_timestamp=publish_ts,
                include_event_context=True,
            )
        else:
            rows = await client.get_attributes(
                type_filter=MISP_ATTRIBUTE_TYPES,
                last="7d",
                limit=5000,
                include_event_context=True,
            )

        nuevos, actualizados, total, tipos = await self._ingest_attributes(rows)

        await r.set(KEY_LAST_SYNC, datetime.now(timezone.utc).isoformat())

        lat_ms = round((time.perf_counter() - t0) * 1000, 2)
        return {
            "nuevos": nuevos,
            "actualizados": actualizados,
            "total": total,
            "tipos_distintos": len(tipos),
            "latencia_ms": lat_ms,
        }

    async def start(self, client: MISPClient) -> None:
        await self.redis_bus.connect()
        logger.info("MISP ingestor en marcha (sync cada %ss)", self.SYNC_INTERVAL)
        while True:
            try:
                stats = await self.sync_once(client)
                logger.info(
                    "MISP sync completada",
                    extra={
                        "extra": {
                            "nuevos": stats["nuevos"],
                            "actualizados": stats["actualizados"],
                            "total": stats["total"],
                            "tipos_distintos": stats["tipos_distintos"],
                            "latencia_ms": stats["latencia_ms"],
                        }
                    },
                )
            except Exception as exc:
                logger.error(
                    "Error en sync MISP",
                    extra={"extra": {"detail": str(exc)}},
                )
            await asyncio.sleep(self.SYNC_INTERVAL)

    async def get_stats(self) -> dict[str, Any]:
        await self.redis_bus.connect()
        r = self.redis_bus.client
        out: dict[str, Any] = {
            "by_list": {},
            "last_sync": None,
            "hits_24h": 0,
        }
        if not r:
            return out

        for short in ("misp_ips", "misp_domains", "misp_urls", "misp_hashes"):
            try:
                out["by_list"][short] = await r.scard(f"blocklist:{short}")
            except Exception:
                out["by_list"][short] = 0

        raw = await r.get(KEY_LAST_SYNC)
        if raw:
            out["last_sync"] = raw if isinstance(raw, str) else str(raw)

        out["hits_24h"] = await self.redis_bus.misp_hits_count_24h()
        return out


async def start(client: MISPClient) -> None:
    """Compatibilidad: delega en MISPIngestor."""
    ingestor = MISPIngestor()
    await ingestor.start(client)
