"""
Gestor de preferencias de notificación (MongoDB + caché Redis sin PII).
NotificationEngine usa este módulo para resolver canales por severidad (con fallback a .env).
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from typing import Any, Callable, Optional

from notifier.models import NotifPreferences, Recipient
from notifier.preferences import _split_csv, load_recipients_from_env
from shared.logger import get_logger

logger = get_logger("notifier.preferences_manager")

COLLECTION = "notif_preferences"
CACHE_TTL_S = 300
CACHE_GEN_KEY = "notif:prefs:gen"
CACHE_MERGED_PREFIX = "notif:prefs:v1:merged:"

SEVERITIES = ("critica", "alta", "media", "baja", "info")

_WS = re.compile(r"[\s,;]+")


def _parse_channels_enabled() -> set[str]:
    raw = (os.getenv("NOTIFY_CHANNELS_ENABLED") or "").strip().lower()
    if not raw:
        return {"email", "whatsapp"}
    parts = {p.strip() for p in _WS.split(raw) if p.strip()}
    return parts & {"email", "whatsapp"} or {"email", "whatsapp"}


def _default_severity_map() -> dict[str, dict[str, bool]]:
    return {
        "critica": {"email_enabled": True, "whatsapp_enabled": True},
        "alta": {"email_enabled": True, "whatsapp_enabled": True},
        "media": {"email_enabled": True, "whatsapp_enabled": False},
        "baja": {"email_enabled": True, "whatsapp_enabled": False},
        "info": {"email_enabled": False, "whatsapp_enabled": False},
    }


DEFAULT_POLICY: dict[str, Any] = {
    "critica": {
        "canales": ["whatsapp", "email"],
        "respetar_silencio": False,
        "dedup_minutes": 0,
    },
    "alta": {
        "canales": ["whatsapp", "email"],
        "respetar_silencio": True,
        "dedup_minutes": 30,
    },
    "media": {
        "canales": ["email"],
        "respetar_silencio": True,
        "dedup_minutes": 60,
    },
    "baja": {
        "canales": ["email"],
        "respetar_silencio": True,
        "agrupar_en_resumen_diario": True,
    },
    "info": {"canales": [], "respetar_silencio": True},
}


def _merge_severity_layers(
    *layers: Optional[dict[str, Any]],
) -> dict[str, dict[str, bool]]:
    base = _default_severity_map()
    for layer in layers:
        if not layer:
            continue
        for sev, data in layer.items():
            if sev not in SEVERITIES or not isinstance(data, dict):
                continue
            cur = base.setdefault(sev, {"email_enabled": False, "whatsapp_enabled": False})
            if "email_enabled" in data:
                cur["email_enabled"] = bool(data["email_enabled"])
            if "whatsapp_enabled" in data:
                cur["whatsapp_enabled"] = bool(data["whatsapp_enabled"])
    enabled = _parse_channels_enabled()
    for sev in list(base.keys()):
        f = base[sev]
        if "email" not in enabled:
            f["email_enabled"] = False
        if "whatsapp" not in enabled:
            f["whatsapp_enabled"] = False
    return base


def _normalize_stored_severities(raw: Any) -> dict[str, dict[str, bool]]:
    if not isinstance(raw, dict):
        return {}
    out: dict[str, dict[str, bool]] = {}
    for sev, data in raw.items():
        if sev not in SEVERITIES or not isinstance(data, dict):
            continue
        out[sev] = {
            "email_enabled": bool(data.get("email_enabled", True)),
            "whatsapp_enabled": bool(data.get("whatsapp_enabled", False)),
        }
    return out


def is_preference_admin_user(user_id: str) -> bool:
    uid = (user_id or "").strip().lower()
    if not uid:
        return False
    extra_ids = {x.strip().lower() for x in _split_csv(os.getenv("NOTIFY_PREFERENCE_ADMIN_IDS", ""))}
    if uid in extra_ids:
        return True
    admin_emails = {e.strip().lower() for e in _split_csv(os.getenv("NOTIFY_ADMIN_EMAILS", "")) if "@" in e}
    if "@" in uid and uid in admin_emails:
        return True
    return False


def validate_user_prefs_not_stripping_critica_admin(user_id: str, merged: dict[str, dict[str, bool]]) -> None:
    if not is_preference_admin_user(user_id):
        return
    c = merged.get("critica") or {}
    if not c.get("email_enabled") and not c.get("whatsapp_enabled"):
        raise ValueError(
            "Los administradores deben mantener al menos un canal activo para severidad critica"
        )


class PreferencesManager:
    """
    Jerarquía: defaults de código -> documento global (Mongo) -> área -> usuario.
    Redis: solo flags efectivos por (recipient_id, severidad, área); invalidación vía gen counter.
    """

    def __init__(
        self,
        mongo_db: Any,
        redis_getter: Callable[[], Any],
    ) -> None:
        self._db = mongo_db
        self._redis_getter = redis_getter

    def _col(self) -> Any:
        return self._db[COLLECTION]

    async def _cache_gen(self) -> str:
        client = self._redis_getter()
        if not client:
            return "0"
        try:
            v = await client.get(CACHE_GEN_KEY)
            return str(v if v is not None else "0")
        except Exception as e:
            logger.warning("prefs cache gen read: %s", e)
            return "0"

    async def _bump_cache_gen(self) -> None:
        client = self._redis_getter()
        if not client:
            return
        try:
            await client.incr(CACHE_GEN_KEY)
        except Exception as e:
            logger.warning("prefs cache gen bump: %s", e)

    async def _load_doc(self, scope: str, key: str) -> Optional[dict[str, dict[str, bool]]]:
        doc = await self._col().find_one({"scope": scope, "key": key})
        if not doc:
            return None
        return _normalize_stored_severities(doc.get("severities"))

    async def _save_doc(self, scope: str, key: str, severities: dict[str, Any]) -> None:
        norm = _normalize_stored_severities(severities)
        now = datetime.now(timezone.utc)
        await self._col().update_one(
            {"scope": scope, "key": key},
            {
                "$set": {
                    "severities": norm,
                    "updated_at": now,
                },
                "$setOnInsert": {"scope": scope, "key": key, "created_at": now},
            },
            upsert=True,
        )

    async def ensure_indexes(self) -> None:
        try:
            await self._col().create_index([("scope", 1), ("key", 1)], unique=True)
        except Exception as e:
            logger.warning("notif_preferences index: %s", e)

    async def get_global_prefs(self) -> dict[str, dict[str, bool]]:
        g = await self._load_doc("global", "default")
        return _merge_severity_layers(g)

    async def get_for_recipient(
        self,
        recipient_id: str,
        severidad: str,
        area: Optional[str] = None,
    ) -> NotifPreferences:
        sev = (severidad or "media").lower()
        if sev not in SEVERITIES:
            sev = "media"
        gen = await self._cache_gen()
        area_key = (area or "").strip() or "-"
        rkey = f"{CACHE_MERGED_PREFIX}{recipient_id}:{sev}:{area_key}:{gen}"
        client = self._redis_getter()
        if client:
            try:
                cached = await client.get(rkey)
                if cached:
                    d = json.loads(cached)
                    return NotifPreferences(
                        email_enabled=bool(d.get("email_enabled")),
                        whatsapp_enabled=bool(d.get("whatsapp_enabled")),
                    )
            except Exception as e:
                logger.warning("prefs cache get: %s", e)

        g = await self._load_doc("global", "default")
        a = await self._load_doc("area", area_key) if area_key != "-" else None
        u = await self._load_doc("user", recipient_id)
        merged = _merge_severity_layers(g, a, u)
        flags = merged.get(sev, {"email_enabled": False, "whatsapp_enabled": False})
        prefs = NotifPreferences(
            email_enabled=flags["email_enabled"],
            whatsapp_enabled=flags["whatsapp_enabled"],
        )
        if client:
            try:
                await client.set(
                    rkey,
                    json.dumps(
                        {
                            "email_enabled": prefs.email_enabled,
                            "whatsapp_enabled": prefs.whatsapp_enabled,
                        }
                    ),
                    ex=CACHE_TTL_S,
                )
            except Exception as e:
                logger.warning("prefs cache set: %s", e)
        return prefs

    async def set_user_preferences(self, user_id: str, prefs: dict[str, Any]) -> dict[str, dict[str, bool]]:
        uid = (user_id or "").strip()
        if not uid:
            raise ValueError("user_id vacío")
        overlay = _normalize_stored_severities(prefs)
        if not overlay:
            await self._col().delete_one({"scope": "user", "key": uid})
            await self._bump_cache_gen()
            return {}
        existing = await self._load_doc("user", uid) or {}
        defaults = _default_severity_map()
        merged_user: dict[str, dict[str, bool]] = {}
        all_keys = set(existing.keys()) | set(overlay.keys())
        for sev in all_keys:
            if sev not in SEVERITIES:
                continue
            base = {**defaults.get(sev, {}), **(existing.get(sev) or {})}
            merged_user[sev] = {**base, **(overlay.get(sev) or {})}
        g = await self._load_doc("global", "default")
        merged_preview = _merge_severity_layers(g, merged_user)
        validate_user_prefs_not_stripping_critica_admin(uid, merged_preview)
        await self._save_doc("user", uid, merged_user)
        await self._bump_cache_gen()
        return await self._load_doc("user", uid) or {}

    async def set_area_preferences(self, area: str, prefs: dict[str, Any]) -> dict[str, dict[str, bool]]:
        key = (area or "").strip()
        if not key:
            raise ValueError("area vacía")
        overlay = _normalize_stored_severities(prefs)
        if not overlay:
            await self._col().delete_one({"scope": "area", "key": key})
            await self._bump_cache_gen()
            return {}
        existing = await self._load_doc("area", key) or {}
        defaults = _default_severity_map()
        merged_area: dict[str, dict[str, bool]] = {}
        all_keys = set(existing.keys()) | set(overlay.keys())
        for sev in all_keys:
            if sev not in SEVERITIES:
                continue
            base = {**defaults.get(sev, {}), **(existing.get(sev) or {})}
            merged_area[sev] = {**base, **(overlay.get(sev) or {})}
        await self._save_doc("area", key, merged_area)
        await self._bump_cache_gen()
        return await self._load_doc("area", key) or {}

    async def set_global_preferences(self, prefs: dict[str, Any]) -> dict[str, dict[str, bool]]:
        overlay = _normalize_stored_severities(prefs)
        if not overlay:
            await self._col().delete_one({"scope": "global", "key": "default"})
            await self._bump_cache_gen()
            return _merge_severity_layers()
        existing = await self._load_doc("global", "default") or {}
        defaults = _default_severity_map()
        merged_g: dict[str, dict[str, bool]] = {}
        all_keys = set(existing.keys()) | set(overlay.keys())
        for sev in all_keys:
            if sev not in SEVERITIES:
                continue
            base = {**defaults.get(sev, {}), **(existing.get(sev) or {})}
            merged_g[sev] = {**base, **(overlay.get(sev) or {})}
        merged_preview = _merge_severity_layers(merged_g)
        crit = merged_preview.get("critica") or {}
        if not crit.get("email_enabled") and not crit.get("whatsapp_enabled"):
            raise ValueError("La política global no puede desactivar todos los canales en critica")
        await self._save_doc("global", "default", merged_g)
        await self._bump_cache_gen()
        return await self.get_global_prefs()

    async def get_global_document(self) -> dict[str, Any]:
        doc = await self._col().find_one({"scope": "global", "key": "default"})
        if not doc:
            return {}
        doc.pop("_id", None)
        return doc

    async def get_user_document(self, user_id: str) -> dict[str, Any]:
        doc = await self._col().find_one({"scope": "user", "key": user_id})
        if not doc:
            return {}
        doc.pop("_id", None)
        return doc

    async def get_area_document(self, area: str) -> dict[str, Any]:
        doc = await self._col().find_one({"scope": "area", "key": area.strip()})
        if not doc:
            return {}
        doc.pop("_id", None)
        return doc


def get_all_admins_from_env() -> list[Recipient]:
    return [r for r in load_recipients_from_env() if r.es_admin]


def get_area_responsible_from_env(area: str) -> Optional[Recipient]:
    key = (area or "").strip().upper().replace(" ", "_")
    if not key:
        return None
    email = (os.getenv(f"NOTIFY_AREA_{key}_EMAIL") or "").strip()
    if not email or "@" not in email:
        return None
    return Recipient(
        id=f"area-{key.lower()}",
        nombre=area.strip(),
        email=email,
        area=area.strip(),
        es_admin=False,
        preferencias=NotifPreferences(),
    )
