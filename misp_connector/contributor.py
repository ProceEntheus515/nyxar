"""
Publicación de IOCs validados hacia MISP (opt-in MISP_CONTRIBUTE).
"""

from __future__ import annotations

import asyncio
import ipaddress
import os
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from urllib.parse import urlparse

from shared.logger import get_logger
from shared.mongo_client import MongoClient
from shared.redis_bus import RedisBus

from enricher.feeds.downloader import FeedDownloader
from misp_connector.client import MISPClient

logger = get_logger("misp_connector.contributor")

COLLECTION_CONTRIBUTED = "misp_contributed_iocs"
EVENT_WINDOW_HOURS = 24
DEFAULT_POLL_S = 60


def _parse_incident_timestamp(raw: Any) -> Optional[datetime]:
    if raw is None:
        return None
    if isinstance(raw, datetime):
        return raw if raw.tzinfo else raw.replace(tzinfo=timezone.utc)
    if isinstance(raw, str):
        try:
            dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except ValueError:
            return None
    return None


def _norm_estado(incident: dict) -> str:
    e = incident.get("estado")
    return str(e).strip().lower() if e is not None else ""


def _norm_severidad(incident: dict) -> str:
    s = incident.get("severidad")
    if s is None:
        return ""
    return str(s).strip().upper().replace("Í", "I")


def _is_private_ip(val: str) -> bool:
    try:
        addr = ipaddress.ip_address(val.strip())
        return bool(
            addr.is_private
            or addr.is_loopback
            or addr.is_link_local
            or addr.is_reserved
        )
    except ValueError:
        return False


def _is_bad_domain_host(val: str) -> bool:
    v = val.lower().strip()
    return v.endswith(".local") or v.endswith(".internal")


def _hash_to_misp_type(val: str) -> str:
    h = val.strip().lower()
    n = len(h)
    if n == 32 and re.fullmatch(r"[a-f0-9]+", h):
        return "md5"
    if n == 40 and re.fullmatch(r"[a-f0-9]+", h):
        return "sha1"
    if n == 64 and re.fullmatch(r"[a-f0-9]+", h):
        return "sha256"
    return "sha256"


def _map_externo_to_misp(externo_tipo: str, valor: str) -> Optional[str]:
    t = externo_tipo.lower()
    if t == "ip":
        return "ip-dst"
    if t == "dominio":
        return "domain"
    if t == "url":
        return "url"
    if t == "hash":
        return _hash_to_misp_type(valor)
    return None


def _sanitize_comment(incident: dict) -> str:
    patron = str(incident.get("patron") or "Threat activity").strip()
    mitre = str(incident.get("mitre_technique") or "").strip()
    base = f"Detectado por CyberPulse — {patron}"
    if mitre:
        base += f" ({mitre})"
    base += ". IOC compartido con fines defensivos."
    return base[:400]


def _tlp_tag() -> str:
    raw = os.getenv("MISP_TLP", "tlp:white").strip().lower()
    if not raw.startswith("tlp:"):
        raw = f"tlp:{raw.replace('tlp:', '')}"
    return raw


def _distribution_level() -> int:
    try:
        d = int(os.getenv("MISP_DISTRIBUTION", "1").strip())
    except ValueError:
        d = 1
    allow_all = os.getenv("MISP_ALLOW_DISTRIBUTION_ALL", "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )
    if d >= 3 and not allow_all:
        logger.warning(
            "MISP_DISTRIBUTION>=3 requiere MISP_ALLOW_DISTRIBUTION_ALL; usando 2",
        )
        return 2
    return max(0, min(d, 3))


class MISPContributor:
    """
    Publica IOCs nuevos y validados de CyberPulse a MISP (MISP_CONTRIBUTE=true).
    """

    def __init__(self) -> None:
        self.mongo = MongoClient()
        self.redis_bus = RedisBus()
        self._feeds: Optional[FeedDownloader] = None

    def _feeds_downloader(self) -> FeedDownloader:
        if self._feeds is None:
            self._feeds = FeedDownloader(self.redis_bus)
        return self._feeds

    def _map_severidad_to_threat_level(self, severidad: str) -> int:
        s = severidad.upper().replace("Í", "I")
        if s in ("CRITICA", "CRÍTICA", "ALTA"):
            return 1
        if s == "MEDIA":
            return 2
        return 3

    async def evaluate_incident(self, incident: dict) -> list[dict]:
        if _norm_estado(incident) != "cerrado":
            return []

        sev = _norm_severidad(incident)
        if sev not in ("ALTA", "CRITICA"):
            return []

        if incident.get("misp_event_id"):
            return []

        db = self.mongo.db
        if db is None:
            return []

        center = _parse_incident_timestamp(incident.get("timestamp"))
        if center is None:
            center = datetime.now(timezone.utc)

        candidates: list[tuple[str, str, str]] = []
        detalles = incident.get("detalles") or {}
        if isinstance(detalles, dict):
            if detalles.get("domain"):
                candidates.append((str(detalles["domain"]), "dominio", "domain"))
            if detalles.get("ip"):
                candidates.append((str(detalles["ip"]), "ip", "ip-dst"))

        eid = incident.get("evento_original_id")
        if eid:
            ev = await db.events.find_one({"id": eid})
            if ev and isinstance(ev.get("externo"), dict):
                ex = ev["externo"]
                v = ex.get("valor")
                t = ex.get("tipo")
                if v and t:
                    mt = _map_externo_to_misp(str(t), str(v))
                    if mt:
                        candidates.append((str(v), str(t), mt))

        seen: set[tuple[str, str]] = set()
        unique_cands: list[tuple[str, str, str]] = []
        for val, ext_tipo, misp_t in candidates:
            key = (val.strip().lower(), misp_t)
            if key in seen:
                continue
            seen.add(key)
            unique_cands.append((val, ext_tipo, misp_t))

        feeds = self._feeds_downloader()
        await self.redis_bus.connect()
        r = self.redis_bus.client

        eligible: list[dict] = []
        for valor, ext_tipo, misp_type in unique_cands:
            if misp_type == "ip-dst" and _is_private_ip(valor):
                continue
            if misp_type == "domain" and _is_bad_domain_host(valor):
                continue
            if misp_type == "url":
                try:
                    p = urlparse(
                        valor if "://" in valor else f"http://{valor}"
                    )
                    if p.hostname and _is_bad_domain_host(p.hostname):
                        continue
                except Exception:
                    pass

            if await self._ioc_on_blocklist(valor, ext_tipo, feeds, r):
                continue

            if not await self._meets_event_count(
                db, valor, ext_tipo, center, incident
            ):
                continue

            tags = ["cyberpulse", "latam"]
            patron_slug = re.sub(
                r"[^a-z0-9]+", "_", str(incident.get("patron", "")).lower()
            ).strip("_")
            if patron_slug:
                tags.append(patron_slug[:40])

            eligible.append(
                {
                    "type": misp_type,
                    "value": valor.strip(),
                    "comment": _sanitize_comment(incident),
                    "to_ids": True,
                    "tags": tags,
                }
            )

        return eligible

    async def _ioc_on_blocklist(
        self,
        valor: str,
        ext_tipo: str,
        feeds: FeedDownloader,
        r: Any,
    ) -> bool:
        et = ext_tipo.lower()
        if et == "ip":
            return (await feeds.check_ip(valor.strip())) is not None
        if et == "dominio":
            return (await feeds.check_domain(valor.strip().lower())) is not None
        if et == "url":
            u = valor.strip()
            if await feeds.check_misp_url(u):
                return True
            try:
                p = urlparse(u if "://" in u else f"http://{u}")
                host = (p.hostname or "").lower()
                if host and await feeds.check_domain(host):
                    return True
            except Exception:
                pass
            return False
        if et == "hash":
            h = valor.strip().lower()
            if await feeds.check_misp_hash(h):
                return True
            if r and await r.sismember("blocklist:threatfox", h):
                return True
            return False
        return False

    async def _meets_event_count(
        self,
        db: Any,
        valor: str,
        ext_tipo: str,
        center: datetime,
        incident: dict,
    ) -> bool:
        detalles = incident.get("detalles") or {}
        if isinstance(detalles, dict):
            hits = detalles.get("hits_detectados")
            if isinstance(hits, (int, float)) and int(hits) >= 2:
                return True

        desde = center - timedelta(hours=EVENT_WINDOW_HOURS)
        hasta = center + timedelta(hours=EVENT_WINDOW_HOURS)
        base = {"externo.valor": valor, "externo.tipo": ext_tipo}
        try:
            n = await db.events.count_documents(
                {
                    **base,
                    "timestamp": {"$gte": desde, "$lte": hasta},
                }
            )
            if n >= 2:
                return True
        except Exception:
            pass
        try:
            n_any = await db.events.count_documents(base)
        except Exception as exc:
            logger.warning(
                "No se pudo contar eventos para IOC; se excluye por seguridad",
                extra={"extra": {"detail": str(exc)}},
            )
            return False
        return n_any >= 2

    async def publish_iocs(
        self,
        iocs: list[dict],
        incident: dict,
        client: MISPClient,
    ) -> Optional[str]:
        if not iocs:
            return None

        db = self.mongo.db
        if db is None:
            return None

        coll_dedupe = db[COLLECTION_CONTRIBUTED]
        to_send: list[dict] = []
        for ioc in iocs:
            v = str(ioc.get("value", "")).strip()
            t = str(ioc.get("type", "")).strip()
            if not v or not t:
                continue
            if t == "ip-dst" and _is_private_ip(v):
                continue
            if t == "domain" and _is_bad_domain_host(v):
                continue
            if t == "url":
                try:
                    p = urlparse(v if "://" in v else f"http://{v}")
                    if p.hostname and _is_bad_domain_host(p.hostname):
                        continue
                except Exception:
                    pass

            exists = await coll_dedupe.find_one({"value": v.lower(), "misp_type": t})
            if exists:
                continue
            to_send.append(ioc)

        if not to_send:
            logger.info(
                "Sin IOCs nuevos para MISP tras deduplicación",
                extra={"extra": {"incident_id": incident.get("id")}},
            )
            return None

        titulo = str(incident.get("patron") or incident.get("id") or "incident")
        info = f"[CyberPulse LATAM] {titulo}"
        sev = self._map_severidad_to_threat_level(_norm_severidad(incident))
        dist = _distribution_level()
        tag_names = [
            _tlp_tag(),
            "cyberpulse:latam",
            "sector:latam",
        ]

        event_payload: dict[str, Any] = {
            "info": info[:255],
            "threat_level_id": sev,
            "analysis": 2,
            "distribution": dist,
            "Tag": [{"name": x} for x in tag_names],
        }

        event_id = await client.create_event(event_payload)
        if not event_id:
            event_id = await client.create_event(
                {
                    "info": info[:255],
                    "threat_level_id": sev,
                    "analysis": 2,
                    "distribution": dist,
                }
            )

        if not event_id:
            logger.error("MISP no devolvió event_id")
            return None

        inc_id = str(incident.get("id") or "")
        contributed_at = datetime.now(timezone.utc).isoformat()

        for ioc in to_send:
            attr = {
                "type": ioc["type"],
                "value": ioc["value"],
                "comment": ioc.get("comment", "")[:400],
                "to_ids": bool(ioc.get("to_ids", True)),
            }
            try:
                ok = await client.add_attribute(event_id, attr)
                if not ok:
                    logger.warning(
                        "add_attribute rechazado por MISP",
                        extra={"extra": {"type": attr["type"]}},
                    )
                    continue
                await coll_dedupe.insert_one(
                    {
                        "value": str(ioc["value"]).strip().lower(),
                        "misp_type": ioc["type"],
                        "incident_id": inc_id,
                        "misp_event_id": str(event_id),
                        "contributed_at": contributed_at,
                    }
                )
            except Exception as exc:
                logger.error(
                    "Error publicando atributo MISP",
                    extra={"extra": {"detail": str(exc)}},
                )

        await db.incidents.update_one(
            {"id": incident.get("id")},
            {
                "$set": {
                    "misp_event_id": str(event_id),
                    "misp_contributed_at": contributed_at,
                }
            },
        )

        logger.info(
            "Evento MISP creado y IOCs publicados",
            extra={
                "extra": {
                    "misp_event_id": event_id,
                    "incident_id": inc_id,
                    "iocs": len(to_send),
                }
            },
        )
        return str(event_id)

    async def _ensure_indexes(self) -> None:
        db = self.mongo.db
        if db is None:
            return
        coll = db[COLLECTION_CONTRIBUTED]
        try:
            await coll.create_index(
                [("value", 1), ("misp_type", 1)],
                unique=True,
                name="misp_ioc_dedupe",
            )
        except Exception as exc:
            logger.warning(
                "Índice misp_contributed_iocs no creado",
                extra={"extra": {"detail": str(exc)}},
            )

    async def _handle_incident_doc(self, client: MISPClient, doc: dict) -> None:
        if not doc:
            return
        if not client.contribute:
            return
        try:
            if doc.get("misp_event_id"):
                return
            if doc.get("misp_contribution_no_iocs"):
                return
            if _norm_estado(doc) != "cerrado":
                return
            iocs = await self.evaluate_incident(doc)
            if not iocs:
                db = self.mongo.db
                if db is not None and doc.get("id"):
                    await db.incidents.update_one(
                        {"id": doc["id"]},
                        {"$set": {"misp_contribution_no_iocs": True}},
                    )
                return
            await self.publish_iocs(iocs, doc, client)
        except Exception as exc:
            logger.error(
                "Fallo procesando incidente para MISP",
                extra={"extra": {"detail": str(exc), "id": doc.get("id")}},
            )

    async def _run_change_stream(self, client: MISPClient) -> None:
        db = self.mongo.db
        if db is None:
            raise RuntimeError("Mongo sin db")
        coll = db.incidents
        logger.info("MISP contributor: Change Stream activo sobre incidents")
        stream = coll.watch(full_document="updateLookup")
        try:
            async for change in stream:
                doc = change.get("fullDocument")
                if not isinstance(doc, dict):
                    continue
                asyncio.create_task(self._handle_incident_doc(client, doc))
        finally:
            closer = getattr(stream, "close", None)
            if closer is not None:
                res = closer()
                if asyncio.iscoroutine(res):
                    await res

    async def _poll_loop(self, client: MISPClient) -> None:
        poll_s = DEFAULT_POLL_S
        try:
            poll_s = max(15, int(os.getenv("MISP_CONTRIBUTOR_POLL_S", str(DEFAULT_POLL_S))))
        except ValueError:
            poll_s = DEFAULT_POLL_S

        db = self.mongo.db
        if db is None:
            return
        coll = db.incidents
        logger.info(
            "MISP contributor: polling cada %ss (incidents cerrados sin misp_event_id)",
            poll_s,
        )
        while True:
            try:
                cursor = coll.find(
                    {
                        "estado": "cerrado",
                        "misp_event_id": {"$exists": False},
                        "misp_contribution_no_iocs": {"$ne": True},
                    }
                )
                async for doc in cursor:
                    asyncio.create_task(self._handle_incident_doc(client, dict(doc)))
            except Exception as exc:
                logger.error(
                    "Error en polling contributor MISP",
                    extra={"extra": {"detail": str(exc)}},
                )
            await asyncio.sleep(poll_s)

    async def start(self, client: MISPClient) -> None:
        if not client.contribute:
            logger.info("MISP contributor deshabilitado (MISP_CONTRIBUTE=false)")
            return

        await self.mongo.connect()
        await self.redis_bus.connect()
        await self._ensure_indexes()

        try:
            await self._run_change_stream(client)
        except Exception as exc:
            logger.warning(
                "Change Stream no disponible; se usa polling",
                extra={"extra": {"detail": str(exc)}},
            )
            await self._poll_loop(client)


async def start(client: MISPClient) -> None:
    contrib = MISPContributor()
    await contrib.start(client)
