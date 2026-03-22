"""
Sincroniza usuarios, equipos y grupos de AD hacia MongoDB (identities).
"""

from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from shared.logger import get_logger
from shared.mongo_client import MongoClient
from shared.redis_bus import RedisBus

from ad_connector.client import ADClient, filetime_to_datetime

logger = get_logger("ad_connector.identity_sync")

CACHE_TTL_HOST_IDENTITY = 86400

_BUILTIN_HIGH_GROUPS = (
    "domain admins",
    "enterprise admins",
    "schema admins",
    "backup operators",
    "server operators",
    "administrators",
)


def _slug_area(department: Optional[str]) -> str:
    s = (department or "").strip().lower().replace(" ", "_")
    s = re.sub(r"[^a-z0-9_]+", "", s)
    return s or "general"


def _cn_from_memberof_dn(dn: str) -> str:
    if not dn:
        return ""
    m = re.match(r"CN=([^,]+)", dn, re.IGNORECASE)
    return (m.group(1).strip() if m else dn).strip()


def _group_cns(member_of: Any) -> List[str]:
    if not member_of:
        return []
    if isinstance(member_of, str):
        items = [member_of]
    else:
        items = list(member_of)
    out: List[str] = []
    for dn in items:
        cn = _cn_from_memberof_dn(str(dn))
        if cn:
            out.append(cn)
    return out


def _is_builtin_admin_group(cn: str) -> bool:
    low = cn.lower()
    return low in _BUILTIN_HIGH_GROUPS or low == "domain admins"


def _patterns_from_env() -> List[str]:
    raw = os.getenv("AD_PRIVILEGED_GROUP_PATTERNS", "admin")
    return [p.strip().lower() for p in raw.split(",") if p.strip()]


class IdentitySync:
    """
    Upsert de identidades desde AD; preserva risk_score y baseline existentes.
    """

    def __init__(
        self,
        mongo_client: MongoClient,
        redis_bus: Optional[RedisBus] = None,
    ) -> None:
        self.mongo = mongo_client
        self.redis = redis_bus

    def _identities(self):
        return self.mongo.db.identities

    def _build_user_identity_id(self, username: str, department: Optional[str]) -> str:
        area = _slug_area(department)
        u = (username or "").strip().lower()
        return f"{area}.{u}" if u else ""

    async def _upsert_identity(
        self,
        identity_id: str,
        set_doc: Dict[str, Any],
        set_on_insert: Dict[str, Any],
    ) -> Tuple[str, Optional[str]]:
        """
        Retorna ("nuevo"|"actualizado"|"sin_cambio"|"error", mensaje_error).
        """
        if not identity_id:
            return "error", "id_vacio"
        col = self._identities()
        try:
            res = await col.update_one(
                {"id": identity_id},
                {
                    "$set": set_doc,
                    "$setOnInsert": set_on_insert,
                },
                upsert=True,
            )
            if res.upserted_id is not None:
                return "nuevo", None
            if res.matched_count and res.modified_count == 0:
                return "sin_cambio", None
            if res.matched_count:
                return "actualizado", None
            return "actualizado", None
        except Exception as e:
            logger.error("Upsert identidad %s: %s", identity_id, e)
            return "error", str(e)

    async def _redis_publish_host(
        self,
        ip: Optional[str],
        usuario: str,
        area: str,
        hostname: str,
    ) -> None:
        if not self.redis or not ip:
            return
        try:
            await self.redis.cache_set(
                f"identities:host:{ip}",
                {
                    "usuario": usuario,
                    "area": area or "unknown",
                    "hostname": hostname or "unknown",
                },
                ttl=CACHE_TTL_HOST_IDENTITY,
            )
        except Exception as e:
            logger.warning("Redis identities:host no actualizado: %s", e)

    def _user_es_admin(self, group_cns: List[str]) -> bool:
        for cn in group_cns:
            low = cn.lower()
            if _is_builtin_admin_group(cn):
                return True
            if low == "administrators":
                return True
        return False

    async def full_sync(self, client: ADClient) -> Dict[str, int]:
        stats = {
            "sincronizados": 0,
            "nuevos": 0,
            "actualizados": 0,
            "errores": 0,
            "sin_cambio": 0,
        }
        now = datetime.now(timezone.utc)

        users = await client.get_all_users()
        dn_to_identity_id: Dict[str, str] = {}

        for u in users:
            sam = u.get("sAMAccountName")
            if not sam:
                stats["errores"] += 1
                continue
            dept = u.get("department")
            identity_id = self._build_user_identity_id(str(sam), str(dept) if dept else None)
            dn = u.get("distinguishedName")
            if isinstance(dn, str) and dn:
                dn_to_identity_id[dn.lower()] = identity_id

            groups = _group_cns(u.get("memberOf"))
            manager_dn = u.get("manager")
            manager_id: Optional[str] = None
            if isinstance(manager_dn, str) and manager_dn.strip():
                manager_id = dn_to_identity_id.get(manager_dn.strip().lower())

            last_logon = filetime_to_datetime(u.get("lastLogon"))
            when_created = u.get("whenCreated")
            if isinstance(when_created, datetime) and when_created.tzinfo is None:
                when_created = when_created.replace(tzinfo=timezone.utc)

            set_doc: Dict[str, Any] = {
                "usuario": str(sam).strip(),
                "nombre_completo": u.get("displayName") or str(sam),
                "email": u.get("mail") or "",
                "area": (str(dept).strip() if dept else "") or "general",
                "cargo": u.get("title") or "",
                "grupos_ad": groups,
                "es_admin": self._user_es_admin(groups),
                "ad_sincronizado": True,
                "ad_ultima_sync": now,
                "ad_last_logon": last_logon,
                "ad_when_created": when_created,
            }
            if manager_id:
                set_doc["manager_id"] = manager_id

            set_on_insert: Dict[str, Any] = {
                "id": identity_id,
                "risk_score": 0,
                "baseline": {},
            }

            status, _ = await self._upsert_identity(identity_id, set_doc, set_on_insert)
            stats["sincronizados"] += 1
            if status == "nuevo":
                stats["nuevos"] += 1
            elif status == "actualizado":
                stats["actualizados"] += 1
            elif status == "sin_cambio":
                stats["sin_cambio"] += 1
            else:
                stats["errores"] += 1

        # Segunda pasada: manager_id si el DN del manager aparecio despues (orden LDAP no garantizado)
        for u in users:
            sam = u.get("sAMAccountName")
            if not sam:
                continue
            dept = u.get("department")
            identity_id = self._build_user_identity_id(str(sam), str(dept) if dept else None)
            manager_dn = u.get("manager")
            if not isinstance(manager_dn, str) or not manager_dn.strip():
                continue
            mid = dn_to_identity_id.get(manager_dn.strip().lower())
            if mid:
                await self._identities().update_one(
                    {"id": identity_id},
                    {"$set": {"manager_id": mid}},
                )

        computers = await client.get_computers()
        for c in computers:
            cn = c.get("cn")
            if not cn:
                continue
            key = re.sub(r"[^a-z0-9._-]+", "_", str(cn).lower())
            cid = f"computer.{key}"
            fqdn = c.get("dNSHostName") or str(cn)
            lts = filetime_to_datetime(c.get("lastLogonTimestamp"))
            set_doc = {
                "usuario": str(cn),
                "nombre_completo": fqdn,
                "email": "",
                "area": "computers",
                "cargo": c.get("operatingSystem") or "",
                "grupos_ad": [],
                "es_admin": False,
                "ad_sincronizado": True,
                "ad_ultima_sync": now,
                "tipo": "computer",
                "hostname": str(cn),
                "ad_last_logon": lts,
                "descripcion_equipo": c.get("description") or "",
            }
            set_on_insert = {
                "id": cid,
                "risk_score": 0,
                "baseline": {},
            }
            status, _ = await self._upsert_identity(cid, set_doc, set_on_insert)
            stats["sincronizados"] += 1
            if status == "nuevo":
                stats["nuevos"] += 1
            elif status == "actualizado":
                stats["actualizados"] += 1
            elif status == "sin_cambio":
                stats["sin_cambio"] += 1
            else:
                stats["errores"] += 1

        _ = await client.get_groups()

        await self.flag_high_privilege_users()

        async for doc in self._identities().find(
            {"ad_sincronizado": True, "ip_asociada": {"$exists": True, "$ne": ""}}
        ):
            await self._redis_publish_host(
                doc.get("ip_asociada"),
                doc.get("usuario") or "unknown",
                doc.get("area") or "unknown",
                doc.get("hostname") or "unknown",
            )

        return stats

    async def refresh_host_cache_from_logons(self, client: ADClient) -> None:
        """
        Actualiza Redis identities:host:{ip} con el ultimo mapa ip->usuario
        (Wazuh logons o fallback identities), para alinear el normalizador.
        """
        if not self.redis:
            return
        rows = await client.get_logged_on_users()
        col = self._identities()
        for r in rows:
            ip = r.get("ip")
            user = r.get("usuario")
            if not ip or not user:
                continue
            area = "unknown"
            try:
                doc = await col.find_one({"usuario": user})
                if not doc:
                    doc = await col.find_one(
                        {"usuario": {"$regex": f"^{re.escape(user)}$", "$options": "i"}}
                    )
                if doc:
                    area = doc.get("area") or "unknown"
            except Exception:
                pass
            await self._redis_publish_host(
                ip,
                user,
                area,
                str(r.get("hostname") or "unknown"),
            )

    async def incremental_sync(self, client: ADClient, desde: datetime) -> Dict[str, int]:
        stats = {
            "sincronizados": 0,
            "nuevos": 0,
            "actualizados": 0,
            "errores": 0,
            "sin_cambio": 0,
        }
        now = datetime.now(timezone.utc)
        users = await client.get_users_modified_since(desde)
        dn_to_identity_id: Dict[str, str] = {}
        for u in users:
            sam = u.get("sAMAccountName")
            if not sam:
                continue
            dept = u.get("department")
            identity_id = self._build_user_identity_id(str(sam), str(dept) if dept else None)
            dn = u.get("distinguishedName")
            if isinstance(dn, str) and dn:
                dn_to_identity_id[dn.lower()] = identity_id

        for u in users:
            sam = u.get("sAMAccountName")
            if not sam:
                stats["errores"] += 1
                continue
            dept = u.get("department")
            identity_id = self._build_user_identity_id(str(sam), str(dept) if dept else None)
            groups = _group_cns(u.get("memberOf"))
            manager_dn = u.get("manager")
            manager_id: Optional[str] = None
            if isinstance(manager_dn, str) and manager_dn.strip():
                manager_id = dn_to_identity_id.get(manager_dn.strip().lower())

            set_doc: Dict[str, Any] = {
                "usuario": str(sam).strip(),
                "nombre_completo": u.get("displayName") or str(sam),
                "email": u.get("mail") or "",
                "area": (str(dept).strip() if dept else "") or "general",
                "cargo": u.get("title") or "",
                "grupos_ad": groups,
                "es_admin": self._user_es_admin(groups),
                "ad_sincronizado": True,
                "ad_ultima_sync": now,
                "ad_last_logon": filetime_to_datetime(u.get("lastLogon")),
            }
            if manager_id:
                set_doc["manager_id"] = manager_id

            set_on_insert = {
                "id": identity_id,
                "risk_score": 0,
                "baseline": {},
            }
            status, _ = await self._upsert_identity(identity_id, set_doc, set_on_insert)
            stats["sincronizados"] += 1
            if status == "nuevo":
                stats["nuevos"] += 1
            elif status == "actualizado":
                stats["actualizados"] += 1
            elif status == "sin_cambio":
                stats["sin_cambio"] += 1
            else:
                stats["errores"] += 1

        await self.flag_high_privilege_users()

        async for doc in self._identities().find(
            {"ad_sincronizado": True, "ip_asociada": {"$exists": True, "$ne": ""}}
        ):
            await self._redis_publish_host(
                doc.get("ip_asociada"),
                doc.get("usuario") or "unknown",
                doc.get("area") or "unknown",
                doc.get("hostname") or "unknown",
            )

        return stats

    async def flag_high_privilege_users(self) -> None:
        patrones = _patterns_from_env()
        fixed_names = {
            "domain admins",
            "enterprise admins",
            "schema admins",
            "backup operators",
            "server operators",
        }

        col = self._identities()
        cursor = col.find({"ad_sincronizado": True, "tipo": {"$ne": "computer"}})
        async for doc in cursor:
            groups: List[str] = list(doc.get("grupos_ad") or [])
            low_list = [g.lower() for g in groups]
            priv = False
            for g in low_list:
                if g in fixed_names:
                    priv = True
                    break
            if not priv:
                for g in low_list:
                    if any(p in g for p in patrones):
                        priv = True
                        break
            await col.update_one(
                {"id": doc["id"]},
                {"$set": {"es_privilegiado": priv}},
            )
