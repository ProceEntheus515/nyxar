"""
Resolucion ip -> identidad en tiempo real: Redis (TTL 5m), wazuh_logons, identities AD.
"""

from __future__ import annotations

import asyncio
import ipaddress
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from shared.logger import get_logger
from shared.mongo_client import MongoClient
from shared.redis_bus import RedisBus

logger = get_logger("ad_connector.resolver")

SESSION_PREFIX = "identity:session:"
CACHE_TTL = 300
MONGO_BUDGET_S = 0.05


def _unknown_payload(ip: str) -> Dict[str, Any]:
    return {
        "ip": ip,
        "usuario": "desconocido",
        "nombre_completo": None,
        "hostname": "desconocido",
        "area": "desconocido",
        "cargo": None,
        "es_privilegiado": False,
        "fuente_resolucion": "desconocido",
    }


def _iso(v: Any) -> Any:
    if isinstance(v, datetime):
        if v.tzinfo is None:
            v = v.replace(tzinfo=timezone.utc)
        return v.isoformat()
    return v


def _json_safe_doc(d: Dict[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for k, v in d.items():
        if isinstance(v, datetime):
            out[k] = _iso(v)
        else:
            out[k] = v
    return out


class IdentityResolver:
    """
    Prioridad: caché Redis -> wazuh_logons -> identities (ip) -> identities (computer).
    """

    def __init__(self, redis_bus: RedisBus, mongo_client: MongoClient) -> None:
        self.redis_bus = redis_bus
        self.mongo_client = mongo_client

    def _session_key(self, ip: str) -> str:
        return f"{SESSION_PREFIX}{ip}"

    async def _update_cache(self, ip: str, identity: Dict[str, Any]) -> None:
        cache_doc = _json_safe_doc(dict(identity))
        try:
            await self.redis_bus.cache_set(
                self._session_key(ip),
                cache_doc,
                ttl=CACHE_TTL,
            )
        except Exception as e:
            logger.warning("No se pudo escribir caché sesión %s: %s", ip, e)

    async def invalidate(self, ip: str) -> None:
        if not ip or ip.lower() == "unknown":
            return
        try:
            await self.redis_bus.cache_delete(self._session_key(ip))
        except Exception as e:
            logger.warning("invalidate sesión %s: %s", ip, e)

    async def _resolve_from_wazuh_logons(self, ip: str) -> Optional[Dict[str, Any]]:
        db = self.mongo_client.db
        if db is None:
            return None
        doc = await db.wazuh_logons.find_one({"ip": ip}, sort=[("ts", -1)])
        if not doc:
            return None
        usuario = (doc.get("usuario") or "").strip() or "desconocido"
        hostname = (doc.get("hostname") or "").strip() or "desconocido"
        ts = doc.get("ts")
        out: Dict[str, Any] = {
            "ip": ip,
            "usuario": usuario,
            "nombre_completo": None,
            "hostname": hostname,
            "area": "desconocido",
            "cargo": None,
            "es_privilegiado": False,
            "fuente_resolucion": "wazuh_logon",
            "desde": ts if isinstance(ts, datetime) else None,
        }
        return out

    async def _resolve_identity_by_ip(self, ip: str) -> Optional[Dict[str, Any]]:
        db = self.mongo_client.db
        if db is None:
            return None
        doc = await db.identities.find_one({"ip_asociada": ip})
        if not doc:
            return None
        return {
            "ip": ip,
            "usuario": (doc.get("usuario") or "desconocido").strip() or "desconocido",
            "nombre_completo": doc.get("nombre_completo"),
            "hostname": (doc.get("hostname") or "desconocido").strip() or "desconocido",
            "area": (doc.get("area") or "desconocido").strip() or "desconocido",
            "cargo": doc.get("cargo"),
            "es_privilegiado": bool(doc.get("es_privilegiado")),
            "fuente_resolucion": "ad_sync",
        }

    async def _resolve_computer_by_hostname(self, hostname: str) -> Optional[Dict[str, Any]]:
        if not hostname or hostname == "desconocido":
            return None
        db = self.mongo_client.db
        if db is None:
            return None
        hn = hostname.strip()
        esc = re.escape(hn)
        doc = await db.identities.find_one(
            {
                "tipo": "computer",
                "$or": [
                    {"hostname": {"$regex": f"^{esc}$", "$options": "i"}},
                    {"usuario": {"$regex": f"^{esc}$", "$options": "i"}},
                ],
            }
        )
        if not doc:
            return None
        area = (doc.get("area") or "desconocido").strip() or "desconocido"
        cn = (doc.get("hostname") or doc.get("usuario") or hn).strip() or hn
        return {
            "ip": "",
            "usuario": "desconocido",
            "nombre_completo": doc.get("nombre_completo"),
            "hostname": cn,
            "area": area,
            "cargo": doc.get("cargo"),
            "es_privilegiado": False,
            "fuente_resolucion": "computer_fallback",
        }

    def _merge_identity_doc(
        self,
        base: Dict[str, Any],
        idoc: Dict[str, Any],
    ) -> None:
        base["nombre_completo"] = base.get("nombre_completo") or idoc.get("nombre_completo")
        if idoc.get("area") and idoc["area"] != "desconocido":
            base["area"] = idoc["area"]
        base["cargo"] = base.get("cargo") or idoc.get("cargo")
        base["es_privilegiado"] = bool(
            base.get("es_privilegiado") or idoc.get("es_privilegiado")
        )
        if idoc.get("usuario") and idoc["usuario"] != "desconocido":
            base["usuario"] = idoc["usuario"]
        if idoc.get("hostname") and idoc["hostname"] != "desconocido":
            base["hostname"] = idoc["hostname"]
        if idoc.get("usuario") not in (None, "desconocido"):
            base["fuente_resolucion"] = "ad_sync"

    async def _enrich_computer_hostname(self, row: Dict[str, Any]) -> None:
        hn = row.get("hostname") or ""
        if hn == "desconocido" or not hn.strip():
            return
        comp = await self._resolve_computer_by_hostname(hn.strip())
        if not comp:
            return
        if row.get("area") in (None, "desconocido"):
            row["area"] = comp["area"]
        if row.get("hostname") in (None, "desconocido") and comp.get("hostname"):
            row["hostname"] = comp["hostname"]
        row["cargo"] = row.get("cargo") or comp.get("cargo")

    async def _mongo_chain(self, ip: str) -> Dict[str, Any]:
        w = await self._resolve_from_wazuh_logons(ip)
        idoc = await self._resolve_identity_by_ip(ip)

        if w:
            if idoc:
                self._merge_identity_doc(w, idoc)
            await self._enrich_computer_hostname(w)
            return w

        if idoc:
            idoc["ip"] = ip
            await self._enrich_computer_hostname(idoc)
            if (
                idoc.get("usuario") == "desconocido"
                and idoc.get("hostname")
                and idoc["hostname"] != "desconocido"
            ):
                idoc["fuente_resolucion"] = "computer_fallback"
            return idoc

        return _unknown_payload(ip)

    async def resolve(self, ip: str) -> Dict[str, Any]:
        ip = (ip or "").strip()
        try:
            ipaddress.IPv4Address(ip)
        except ValueError:
            return _unknown_payload(ip or "0.0.0.0")

        try:
            cached = await self.redis_bus.cache_get(self._session_key(ip))
            if cached and isinstance(cached, dict) and cached.get("ip") == ip:
                cached = dict(cached)
                cached["fuente_resolucion"] = "cache"
                return cached
        except Exception as e:
            logger.debug("Lectura caché sesión %s: %s", ip, e)

        try:
            result = await asyncio.wait_for(self._mongo_chain(ip), timeout=MONGO_BUDGET_S)
        except asyncio.TimeoutError:
            logger.debug("Mongo resolve timeout para ip=%s", ip)
            result = _unknown_payload(ip)
        except Exception as e:
            logger.warning("Error resolviendo identidad %s: %s", ip, e)
            result = _unknown_payload(ip)

        result["ip"] = ip
        if result.get("fuente_resolucion") != "cache":
            await self._update_cache(ip, result)
        return result

    async def get_all_active_sessions(self) -> List[Dict[str, Any]]:
        try:
            keys = await self.redis_bus.cache_scan_keys(f"{SESSION_PREFIX}*")
        except Exception as e:
            logger.error("SCAN sesiones: %s", e)
            return []
        out: List[Dict[str, Any]] = []
        for key in keys:
            data = await self.redis_bus.cache_get(key)
            if data and isinstance(data, dict):
                out.append(data)
        return out
