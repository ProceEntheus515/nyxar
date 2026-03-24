"""
Motor central de notificaciones multi-canal (email y WhatsApp; sin Slack).
"""

from __future__ import annotations

import asyncio
import json
import os
import uuid
from datetime import datetime, time, timezone
from typing import Literal, Optional

from notifier.channels.email import EmailChannel
from notifier.channels.whatsapp import WhatsAppChannel
from notifier.models import NotifMessage, NotifPreferences, Recipient, SeveridadNotif
from notifier.preferences import load_recipients_from_env
from notifier.preferences_manager import PreferencesManager
from shared.logger import get_logger
from shared.mongo_client import MongoClient
from shared.redis_bus import RedisBus
from shared.heartbeat import heartbeat_loop

logger = get_logger("notifier.engine")

LOG_COLLECTION = "notifications_log"

CHANNEL_URGENT = "notifications:urgent"
CHANNEL_REPORTS = "notifications:reports"
CHANNEL_DASHBOARD_ALERTS = "dashboard:alerts"
CHANNEL_APPROVALS_PENDING = "approvals:pending"


def _norm_sev(s: str | None) -> SeveridadNotif:
    if not s:
        return "media"
    u = str(s).upper().replace("Í", "I")
    if u == "CRITICA":
        return "critica"
    if u == "ALTA":
        return "alta"
    if u == "MEDIA":
        return "media"
    if u == "BAJA":
        return "baja"
    return "info"


class NotificationEngine:
    """
    Decide qué notificar, a quién y por qué canal (email / WhatsApp).
    Escucha Redis PubSub y Change Streams de MongoDB.
    """

    DEDUP_TTL = 900

    def __init__(self) -> None:
        self.redis_bus = RedisBus()
        self.mongo = MongoClient()
        self._recipients_cache: list[Recipient] = []
        self._running = False
        self._email_ch = EmailChannel()
        self._wa_ch = WhatsAppChannel(redis_client_getter=lambda: self.redis_bus.client)
        self._prefs_manager: Optional[PreferencesManager] = None
        self._prefs_manager_init_failed: bool = False

    def _load_recipients(self) -> list[Recipient]:
        self._recipients_cache = load_recipients_from_env()
        return self._recipients_cache

    def _parse_hhmm(self, raw: str, default: time) -> time:
        raw = (raw or "").strip()
        if not raw:
            return default
        parts = raw.replace(".", ":").split(":")
        try:
            h = int(parts[0])
            m = int(parts[1]) if len(parts) > 1 else 0
            return time(h % 24, min(59, max(0, m)))
        except (ValueError, IndexError):
            return default

    def _is_quiet_hours(self) -> bool:
        start = self._parse_hhmm(os.getenv("NOTIFY_QUIET_START", "23:00"), time(23, 0))
        end = self._parse_hhmm(os.getenv("NOTIFY_QUIET_END", "07:00"), time(7, 0))
        now = datetime.now().time()
        if start <= end:
            return start <= now < end
        return now >= start or now < end

    async def _dedup_should_skip(self, evento_tipo: str, objetivo: str) -> bool:
        if not self.redis_bus.client:
            return False
        key = f"notif:dedup:{evento_tipo}:{objetivo}"
        try:
            return bool(await self.redis_bus.client.exists(key))
        except Exception as e:
            logger.warning("_dedup_should_skip: %s", e)
            return False

    async def _dedup_mark(self, evento_tipo: str, objetivo: str) -> None:
        if not self.redis_bus.client:
            return
        key = f"notif:dedup:{evento_tipo}:{objetivo}"
        try:
            await self.redis_bus.client.set(key, "1", ex=self.DEDUP_TTL)
        except Exception as e:
            logger.warning("_dedup_mark: %s", e)

    async def _allow_global_minute(self) -> bool:
        if not self.redis_bus.client:
            return True
        key = "notif:throttle:global_minute"
        try:
            n = await self.redis_bus.client.incr(key)
            if n == 1:
                await self.redis_bus.client.expire(key, 60)
            return n <= 10
        except Exception as e:
            logger.warning("_allow_global_minute: %s", e)
            return True

    async def _allow_whatsapp_hour(self) -> bool:
        if not self.redis_bus.client:
            return True
        key = "notif:throttle:whatsapp_hour"
        try:
            n = await self.redis_bus.client.incr(key)
            if n == 1:
                await self.redis_bus.client.expire(key, 3600)
            return n <= 5
        except Exception as e:
            logger.warning("_allow_whatsapp_hour: %s", e)
            return True

    def _resolve_recipients(self, evento_tipo: str, payload: dict) -> list[Recipient]:
        recs = self._load_recipients()
        admins = [r for r in recs if r.es_admin]
        security = [r for r in recs if "security" in r.id]
        reports = [r for r in recs if "report" in r.id]

        if evento_tipo == "honeypot_hit":
            return admins

        if evento_tipo == "reporte_listo":
            return reports if reports else admins

        if evento_tipo in ("aprobacion_pendiente", "notifications_urgent"):
            return admins

        if evento_tipo.startswith("incidente_"):
            sev = _norm_sev(payload.get("severidad"))
            if sev == "critica":
                return admins + security
            if sev == "alta":
                out = []
                seen = set()
                for r in security + recs:
                    if r.id not in seen:
                        seen.add(r.id)
                        out.append(r)
                return out or admins
            if sev in ("media", "baja", "info"):
                return security if security else admins

        return admins

    async def _get_prefs_manager(self) -> Optional[PreferencesManager]:
        if self._prefs_manager_init_failed:
            return None
        if self._prefs_manager is not None:
            return self._prefs_manager
        try:
            await self.mongo.connect()
            pm = PreferencesManager(self.mongo.db, lambda: self.redis_bus.client)
            await pm.ensure_indexes()
            self._prefs_manager = pm
            return pm
        except Exception as e:
            logger.warning("PreferencesManager no disponible, se usan preferencias del recipient: %s", e)
            self._prefs_manager_init_failed = True
            return None

    async def _effective_prefs_for_recipient(
        self,
        severidad: SeveridadNotif,
        recipient: Recipient,
        area_override: Optional[str] = None,
    ) -> NotifPreferences:
        pm = await self._get_prefs_manager()
        if pm is None:
            return recipient.preferencias
        area_raw = area_override if area_override is not None else recipient.area
        area = str(area_raw).strip() if area_raw else None
        try:
            return await pm.get_for_recipient(recipient.id, severidad, area=area)
        except Exception as e:
            logger.warning("get_for_recipient fallo, fallback .env: %s", e)
            return recipient.preferencias

    async def _select_channels(
        self,
        severidad: SeveridadNotif,
        recipient: Recipient,
        es_horario_silencio: bool,
        area_override: Optional[str] = None,
    ) -> list[str]:
        pref = await self._effective_prefs_for_recipient(severidad, recipient, area_override=area_override)
        ch: list[str] = []

        if severidad == "info":
            return []

        if severidad == "baja":
            return []

        if severidad == "media":
            if pref.email_enabled and recipient.email:
                ch.append("email")
            return ch

        if severidad == "alta":
            if es_horario_silencio:
                if pref.email_enabled and recipient.email:
                    ch.append("email")
                return ch
            if pref.email_enabled and recipient.email:
                ch.append("email")
            if pref.whatsapp_enabled and recipient.whatsapp_number:
                ch.append("whatsapp")
            return ch

        if severidad == "critica":
            if pref.email_enabled and recipient.email:
                ch.append("email")
            if pref.whatsapp_enabled and recipient.whatsapp_number:
                ch.append("whatsapp")
            return ch

        return ch

    @staticmethod
    def _map_notif_tipo(
        evento_tipo: str,
    ) -> Literal["alerta", "reporte", "aprobacion", "resolucion"]:
        if evento_tipo == "reporte_listo":
            return "reporte"
        if evento_tipo == "aprobacion_pendiente":
            return "aprobacion"
        if "resolucion" in evento_tipo:
            return "resolucion"
        return "alerta"

    def _build_dashboard_link(self, evento_tipo: str, payload: dict) -> Optional[str]:
        base = (os.getenv("NOTIFY_DASHBOARD_BASE_URL") or "").strip().rstrip("/")
        if not base:
            return None
        if evento_tipo == "aprobacion_pendiente":
            proposal = payload.get("proposal_id") or payload.get("id")
            if proposal:
                return f"{base}/approvals?proposal={proposal}"
        proposal = payload.get("proposal_id")
        if proposal:
            return f"{base}/approvals?proposal={proposal}"
        iid = payload.get("id") or payload.get("incident_id")
        if iid:
            return f"{base}/incidents/{iid}"
        return base

    def _build_notif_message(
        self,
        evento_tipo: str,
        sev: SeveridadNotif,
        payload: dict,
        subject: str,
        body_email: str,
    ) -> NotifMessage:
        tipo = self._map_notif_tipo(evento_tipo)
        sev_label = str(payload.get("severidad") or sev).strip().upper() or str(sev).upper()
        link = self._build_dashboard_link(evento_tipo, payload)
        corto = WhatsAppChannel._truncate_for_whatsapp(str(body_email), 200)
        raw_attach = payload.get("attachment_path") or payload.get("pdf_path")
        attach = str(raw_attach).strip() if raw_attach else None
        iid = payload.get("id") or payload.get("incident_id")
        incident_id = str(iid).strip() if iid else None
        pid = payload.get("proposal_id")
        if not pid and evento_tipo == "aprobacion_pendiente":
            pid = payload.get("id")
        proposal_id = str(pid).strip() if pid else None
        return NotifMessage(
            tipo=tipo,
            severidad=sev_label,
            titulo=subject[:200],
            cuerpo=str(body_email)[:4000],
            cuerpo_corto=corto,
            link=link,
            incident_id=incident_id,
            proposal_id=proposal_id,
            attachment_path=attach,
        )

    async def _send(
        self,
        channels: list[str],
        recipient: Recipient,
        mensaje: NotifMessage,
    ) -> tuple[list[str], bool]:
        """
        Envía por canales elegidos; si uno falla, intenta el otro si estaba disponible.
        """
        ok_any = False
        used: list[str] = []

        async def try_email() -> bool:
            if not recipient.email:
                return False
            return await self._email_ch.send(recipient, mensaje)

        async def try_wa() -> bool:
            if not recipient.whatsapp_number:
                return False
            if not await self._allow_whatsapp_hour():
                logger.warning("Límite WhatsApp/hora alcanzado; omitiendo WA")
                return False
            return await self._wa_ch.send(recipient, mensaje)

        for ch in channels:
            if ch == "email":
                if await try_email():
                    ok_any = True
                    used.append("email")
            elif ch == "whatsapp":
                if await try_wa():
                    ok_any = True
                    used.append("whatsapp")

        if not ok_any and channels:
            for fallback in ("email", "whatsapp"):
                if fallback not in channels:
                    continue
                if fallback == "email" and "email" not in used:
                    if await try_email():
                        ok_any = True
                        used.append("email(fallback)")
                        break
                if fallback == "whatsapp" and "whatsapp" not in used:
                    if recipient.whatsapp_number and await try_wa():
                        ok_any = True
                        used.append("whatsapp(fallback)")
                        break

        return used, ok_any

    async def _log(
        self,
        evento_tipo: str,
        objetivo: str,
        canales: list[str],
        ok: bool,
        extra: Optional[dict] = None,
    ) -> None:
        doc = {
            "id": f"nlog_{uuid.uuid4().hex[:12]}",
            "ts": datetime.now(timezone.utc).isoformat(),
            "evento_tipo": evento_tipo,
            "objetivo": objetivo,
            "canales": canales,
            "ok": ok,
            "extra": extra or {},
        }
        try:
            await self.mongo.db[LOG_COLLECTION].insert_one(doc)
        except Exception as e:
            logger.error("notifications_log insert: %s", e)

    async def process_event(self, evento_tipo: str, payload: dict) -> None:
        quiet = self._is_quiet_hours()

        sev: SeveridadNotif = _norm_sev(payload.get("severidad"))
        if evento_tipo == "honeypot_hit":
            sev = "critica"
        if evento_tipo in ("reporte_listo", "aprobacion_pendiente", "notifications_urgent"):
            sev = "alta"

        if quiet and evento_tipo != "honeypot_hit":
            if sev in ("media", "baja", "info") and evento_tipo.startswith("incidente"):
                logger.debug("Silencio: omitido %s (%s)", evento_tipo, sev)
                await self._log(evento_tipo, str(payload.get("id")), [], True, {"skipped": "quiet_hours"})
                return

        if evento_tipo not in ("honeypot_hit",) and not await self._allow_global_minute():
            if sev != "critica":
                logger.warning("Throttling global: omitido %s", evento_tipo)
                await self._log(evento_tipo, str(payload.get("id")), [], False, {"skipped": "global_throttle"})
                return

        dedup_obj = str(
            payload.get("dedup_key") or payload.get("id") or payload.get("incident_id") or "unknown"
        )
        if evento_tipo != "honeypot_hit":
            if await self._dedup_should_skip(evento_tipo, dedup_obj):
                logger.debug("Dedup: ya notificado %s %s", evento_tipo, dedup_obj)
                return

        recipients = self._resolve_recipients(evento_tipo, payload)
        if not recipients:
            logger.warning("Sin destinatarios para %s", evento_tipo)
            return

        subject = payload.get("titulo") or payload.get("patron") or "Notificación NYXAR"
        body_email = payload.get("mensaje_email") or payload.get("descripcion") or subject
        if sev == "critica" or evento_tipo == "honeypot_hit":
            body_email = (body_email or "")[:4000]

        subj = str(subject)[:200]
        body = str(body_email)
        mensaje = self._build_notif_message(evento_tipo, sev, payload, subj, body)

        area_from_payload = payload.get("area")
        area_override = str(area_from_payload).strip() if area_from_payload else None

        any_ok = False
        for r in recipients:
            channels = await self._select_channels(sev, r, quiet, area_override=area_override)
            if not channels:
                await self._log(evento_tipo, r.id, [], True, {"skipped": "no_channels", "sev": sev})
                continue
            used, ok = await self._send(channels, r, mensaje)
            if ok:
                any_ok = True
            await self._log(evento_tipo, r.id, used, ok, {"recipient": r.nombre})

        if any_ok and evento_tipo != "honeypot_hit":
            await self._dedup_mark(evento_tipo, dedup_obj)

    @staticmethod
    def _merge_pubsub_payload(payload: dict) -> dict:
        """
        Unifica envelope {tipo, data} con payload plano (p. ej. playbook notify).
        El tipo del envelope se conserva en la clave tipo cuando aplica.
        """
        inner = payload.get("data")
        if isinstance(inner, dict):
            merged = {**inner}
            if payload.get("tipo") is not None:
                merged["tipo"] = payload["tipo"]
            return merged
        return payload

    async def _handle_incident_alert(self, payload: dict) -> None:
        """Canal notifications:urgent: alertas de alta prioridad hacia destinatarios admin."""
        merged = self._merge_pubsub_payload(payload)
        await self.process_event("notifications_urgent", merged)

    async def _handle_report_ready(self, payload: dict) -> None:
        merged = self._merge_pubsub_payload(payload)
        await self.process_event("reporte_listo", merged)

    async def _handle_dashboard_alert_incident(self, data: dict) -> None:
        """
        dashboard:alerts solo dispara notificación si severidad es crítica o alta
        (misma dedup que change stream: id:severidad_normalizada).
        """
        sev = _norm_sev(data.get("severidad"))
        if sev not in ("critica", "alta"):
            logger.debug("dashboard:alerts omitido (severidad=%s)", sev)
            return
        iid = str(data.get("id") or data.get("_id") or "").strip()
        if not iid:
            logger.warning("dashboard:alerts sin id de incidente, se omite")
            return
        await self.process_event(
            f"incidente_{sev}",
            {**data, "dedup_key": f"{iid}:{sev}", "id": iid},
        )

    async def _route_pubsub_message(self, canal: str, raw: dict) -> None:
        """Enruta mensaje PubSub según canal (contrato I13)."""
        if canal == CHANNEL_URGENT:
            await self._handle_incident_alert(raw)
            return
        if canal == CHANNEL_REPORTS:
            await self._handle_report_ready(raw)
            return
        if canal == CHANNEL_DASHBOARD_ALERTS:
            inner = raw.get("data") if isinstance(raw.get("data"), dict) else raw
            if not inner:
                return
            sev = _norm_sev(inner.get("severidad"))
            if sev in ("critica", "alta"):
                await self._handle_dashboard_alert_incident(inner)
            return
        if canal == CHANNEL_APPROVALS_PENDING:
            merged = self._merge_pubsub_payload(raw)
            await self.process_event("aprobacion_pendiente", merged)

    async def _pubsub_loop(self) -> None:
        await self.redis_bus.connect()
        if not self.redis_bus.client:
            logger.error("Redis no disponible: pubsub notificaciones detenido")
            return
        pubsub = self.redis_bus.client.pubsub()
        await pubsub.subscribe(
            CHANNEL_URGENT,
            CHANNEL_REPORTS,
            CHANNEL_DASHBOARD_ALERTS,
            CHANNEL_APPROVALS_PENDING,
        )
        logger.info(
            "PubSub notificaciones: %s, %s, %s, %s",
            CHANNEL_URGENT,
            CHANNEL_REPORTS,
            CHANNEL_DASHBOARD_ALERTS,
            CHANNEL_APPROVALS_PENDING,
        )
        try:
            async for message in pubsub.listen():
                if message["type"] != "message":
                    continue
                raw = message["data"]
                if isinstance(raw, bytes):
                    raw = raw.decode("utf-8", errors="replace")
                try:
                    data = json.loads(raw)
                except json.JSONDecodeError:
                    data = {"raw": raw}
                ch = message.get("channel")
                if isinstance(ch, bytes):
                    ch = ch.decode("utf-8", errors="replace")
                if not isinstance(data, dict):
                    data = {"raw": data}
                await self._route_pubsub_message(ch, data)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error("PubSub notificaciones: %s", e)
        finally:
            await pubsub.unsubscribe(
                CHANNEL_URGENT,
                CHANNEL_REPORTS,
                CHANNEL_DASHBOARD_ALERTS,
                CHANNEL_APPROVALS_PENDING,
            )
            await pubsub.close()

    async def _dispatch_incident_change(self, change: dict) -> None:
        op = change.get("operationType")
        doc = change.get("fullDocument") or {}
        if op == "insert":
            dedup = doc.get("id") or str(doc.get("_id", ""))
            sev = _norm_sev(doc.get("severidad"))
            payload = {**doc, "dedup_key": f"{dedup}:{sev}", "id": dedup}
            await self.process_event(f"incidente_{sev}", payload)
            return
        if op in ("update", "replace") and doc:
            before = change.get("fullDocumentBeforeChange") or {}
            sev_old = _norm_sev(before.get("severidad"))
            sev_new = _norm_sev(doc.get("severidad"))
            order = {"info": 0, "baja": 1, "media": 2, "alta": 3, "critica": 4}
            if order.get(sev_new, 0) > order.get(sev_old, 0):
                iid = doc.get("id") or str(doc.get("_id", ""))
                await self.process_event(
                    f"incidente_{sev_new}",
                    {**doc, "dedup_key": f"{iid}:escalada:{sev_new}", "id": iid},
                )

    async def _watch_collection(self, collection_name: str, _tipo_insert: str, _tipo_update: str) -> None:
        await self.mongo.connect()
        col = self.mongo.db[collection_name]
        pipeline = [{"$match": {"operationType": {"$in": ["insert", "update", "replace"]}}}]
        try:
            async with col.watch(
                pipeline,
                full_document="updateLookup",
                full_document_before_change="whenAvailable",
            ) as stream:
                async for change in stream:
                    await self._dispatch_incident_change(change)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.warning("Change stream %s (modo compatibilidad, sin escalada en updates): %s", collection_name, e)
            try:
                ins_only = [{"$match": {"operationType": "insert"}}]
                async with col.watch(ins_only, full_document="updateLookup") as stream:
                    async for change in stream:
                        await self._dispatch_incident_change(change)
            except asyncio.CancelledError:
                raise
            except Exception as e2:
                logger.error("Change stream %s no disponible (¿replica set?): %s", collection_name, e2)

    async def _watch_honeypots(self) -> None:
        await self.mongo.connect()
        col = self.mongo.db["honeypot_hits"]
        pipeline = [{"$match": {"operationType": "insert"}}]
        try:
            async with col.watch(pipeline) as stream:
                async for change in stream:
                    doc = change.get("fullDocument") or {}
                    await self.process_event(
                        "honeypot_hit",
                        {
                            "id": doc.get("id"),
                            "titulo": "Honeypot activado",
                            "severidad": "CRÍTICA",
                            "descripcion": doc.get("descripcion", "Trampa tocada"),
                        },
                    )
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error("Change stream honeypot_hits: %s", e)

    async def start(self) -> None:
        """
        Arranca tareas en paralelo: PubSub Redis y change streams (incidents + honeypot_hits).
        """
        self._running = True
        await self.mongo.connect()
        await self.redis_bus.connect()
        self._load_recipients()

        tasks = [
            asyncio.create_task(heartbeat_loop(self.redis_bus, "notifier"), name="notif-hb"),
            asyncio.create_task(self._pubsub_loop(), name="notif-pubsub"),
            asyncio.create_task(self._watch_collection("incidents", "insert", "update"), name="notif-incidents"),
            asyncio.create_task(self._watch_honeypots(), name="notif-honeypot"),
        ]
        logger.info("NotificationEngine iniciado (%s tareas)", len(tasks))
        try:
            await asyncio.gather(*tasks)
        except asyncio.CancelledError:
            for t in tasks:
                t.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            raise
        finally:
            self._running = False
