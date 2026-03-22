"""
Cliente LDAP para Active Directory (y OpenLDAP basico) usando ldap3.
Operaciones bloqueantes ejecutadas en asyncio.to_thread; timeouts en la conexion.
"""

from __future__ import annotations

import asyncio
import os
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from ldap3 import (
    ALL,
    AUTO_BIND_NO_TLS,
    AUTO_BIND_TLS_BEFORE_BIND,
    MODIFY_REPLACE,
    SUBTREE,
    Connection,
    Server,
)
from ldap3.utils.conv import escape_filter_chars

from shared.logger import get_logger
from shared.mongo_client import MongoClient

logger = get_logger("ad_connector.client")

DISABLED_UAC_BIT = 2

USER_FILTER = (
    "(&(objectClass=user)(objectCategory=person)"
    "(!(userAccountControl:1.2.840.113556.1.4.803:=%s)))"
) % DISABLED_UAC_BIT

COMPUTER_FILTER = (
    "(&(objectClass=computer)"
    "(!(userAccountControl:1.2.840.113556.1.4.803:=%s)))"
) % DISABLED_UAC_BIT

GROUP_FILTER = (
    "(&(objectClass=group)(groupType:1.2.840.113556.1.4.803:=2147483648))"
)


def filetime_to_datetime(value: Any) -> Optional[datetime]:
    """
    Convierte FILETIME de Windows (100-ns desde 1601-01-01 UTC) a datetime UTC.
    """
    if value is None:
        return None
    try:
        if isinstance(value, datetime):
            if value.tzinfo is None:
                return value.replace(tzinfo=timezone.utc)
            return value.astimezone(timezone.utc)
        if isinstance(value, (list, tuple)) and value:
            value = value[0]
        n = int(value)
    except (TypeError, ValueError):
        return None
    if n <= 0:
        return None
    epoch = datetime(1601, 1, 1, tzinfo=timezone.utc)
    return epoch + timedelta(microseconds=n // 10)


def generalized_time_utc(dt: datetime) -> str:
    """Formato GeneralizedTime para filtros LDAP en AD (whenChanged)."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt.strftime("%Y%m%d%H%M%S.0Z")


class ADClient:
    """
    Cliente LDAP; metodos publicos async. Configuracion por variables de entorno AD_*.
    """

    USER_ATTRIBUTES = [
        "sAMAccountName",
        "displayName",
        "mail",
        "department",
        "title",
        "manager",
        "memberOf",
        "lastLogon",
        "userWorkstations",
        "whenCreated",
        "whenChanged",
        "distinguishedName",
    ]

    COMPUTER_ATTRIBUTES = [
        "cn",
        "dNSHostName",
        "operatingSystem",
        "lastLogonTimestamp",
        "description",
        "distinguishedName",
    ]

    GROUP_ATTRIBUTES = ["cn", "description", "member"]

    def __init__(self, mongo_client: Optional[MongoClient] = None) -> None:
        self.host = os.getenv("AD_SERVER", "").strip()
        self.port = int(os.getenv("AD_PORT", "389"))
        self.use_ssl = os.getenv("AD_USE_SSL", "false").lower() in ("1", "true", "yes")
        self.base_dn = os.getenv("AD_BASE_DN", "").strip()
        self.bind_user = os.getenv("AD_USER", "").strip()
        self.bind_password = os.getenv("AD_PASSWORD", "")
        self.mongo_client = mongo_client

        self._server: Optional[Server] = None
        self._conn: Optional[Connection] = None

    def is_configured(self) -> bool:
        return bool(self.host and self.base_dn and self.bind_user and self.bind_password)

    def _close_sync(self) -> None:
        if self._conn is not None:
            try:
                self._conn.unbind()
            except Exception:
                pass
            self._conn = None

    def _ensure_bound_sync(self) -> bool:
        for attempt in range(3):
            try:
                if self._conn is not None and self._conn.bound:
                    return True
                self._close_sync()
                self._server = Server(
                    self.host,
                    port=self.port,
                    use_ssl=self.use_ssl,
                    get_info=ALL,
                )
                auto = (
                    AUTO_BIND_TLS_BEFORE_BIND
                    if self.use_ssl
                    else AUTO_BIND_NO_TLS
                )
                self._conn = Connection(
                    self._server,
                    user=self.bind_user,
                    password=self.bind_password,
                    auto_bind=auto,
                    receive_timeout=10,
                )
                if self._conn.bound:
                    return True
            except Exception as e:
                logger.warning(
                    "Intento LDAP bind %s/3 fallo: %s",
                    attempt + 1,
                    e,
                )
                time.sleep(0.5 * (attempt + 1))
        return False

    def _search_entries_sync(
        self,
        search_filter: str,
        attributes: List[str],
    ) -> List[Dict[str, Any]]:
        if not self._ensure_bound_sync():
            raise RuntimeError("No se pudo enlazar al servidor LDAP")
        assert self._conn is not None
        ok = self._conn.search(
            self.base_dn,
            search_filter,
            search_scope=SUBTREE,
            attributes=attributes,
        )
        if not ok:
            logger.error(
                "LDAP search fallo: %s",
                self._conn.result,
            )
            return []
        rows: List[Dict[str, Any]] = []
        for entry in self._conn.entries:
            raw = entry.entry_attributes_as_dict
            row: Dict[str, Any] = {}
            for k, vals in raw.items():
                if isinstance(vals, list) and len(vals) == 1:
                    row[k] = vals[0]
                else:
                    row[k] = vals
            rows.append(row)
        return rows

    async def connect(self) -> bool:
        """Conecta y hace bind; True si la sesion LDAP queda activa."""

        def _run() -> bool:
            return self._ensure_bound_sync()

        return await asyncio.to_thread(_run)

    async def get_all_users(self) -> List[Dict[str, Any]]:
        def _run() -> List[Dict[str, Any]]:
            return self._search_entries_sync(USER_FILTER, self.USER_ATTRIBUTES)

        return await asyncio.to_thread(_run)

    async def get_users_modified_since(self, since: datetime) -> List[Dict[str, Any]]:
        gc = generalized_time_utc(since)
        filt = (
            "(&(objectClass=user)(objectCategory=person)"
            "(!(userAccountControl:1.2.840.113556.1.4.803:=%s))"
            "(whenChanged>=%s))"
        ) % (DISABLED_UAC_BIT, gc)

        def _run() -> List[Dict[str, Any]]:
            return self._search_entries_sync(filt, self.USER_ATTRIBUTES)

        return await asyncio.to_thread(_run)

    async def get_computers(self) -> List[Dict[str, Any]]:
        def _run() -> List[Dict[str, Any]]:
            return self._search_entries_sync(
                COMPUTER_FILTER,
                self.COMPUTER_ATTRIBUTES,
            )

        return await asyncio.to_thread(_run)

    async def get_groups(self) -> List[Dict[str, Any]]:
        def _run() -> List[Dict[str, Any]]:
            return self._search_entries_sync(GROUP_FILTER, self.GROUP_ATTRIBUTES)

        return await asyncio.to_thread(_run)

    async def get_logged_on_users(self) -> List[Dict[str, Any]]:
        """
        Mapa ip->usuario: primero wazuh_logons (ultimo por IP); si no hay datos,
        identidades Mongo con ip_asociada y usuario.
        """
        out: List[Dict[str, Any]] = []
        if self.mongo_client and self.mongo_client.db is not None:
            coll = self.mongo_client.db.wazuh_logons
            pipeline = [
                {"$sort": {"ts": -1}},
                {
                    "$group": {
                        "_id": "$ip",
                        "usuario": {"$first": "$usuario"},
                        "hostname": {"$first": "$hostname"},
                        "desde": {"$first": "$ts"},
                    }
                },
            ]
            try:
                async for row in coll.aggregate(pipeline):
                    ip = row.get("_id")
                    if not ip:
                        continue
                    desde = row.get("desde")
                    if isinstance(desde, datetime) and desde.tzinfo is None:
                        desde = desde.replace(tzinfo=timezone.utc)
                    out.append(
                        {
                            "ip": ip,
                            "usuario": row.get("usuario") or "unknown",
                            "hostname": row.get("hostname") or "unknown",
                            "desde": desde,
                        }
                    )
            except Exception as e:
                logger.error("Error agregando wazuh_logons: %s", e)

        if out:
            return out

        if self.mongo_client and self.mongo_client.db is not None:
            col = self.mongo_client.db.identities
            try:
                cursor = col.find(
                    {
                        "ip_asociada": {"$exists": True, "$ne": ""},
                        "usuario": {"$exists": True, "$ne": ""},
                    }
                )
                async for doc in cursor:
                    ip = doc.get("ip_asociada")
                    user = doc.get("usuario")
                    if not ip or not user:
                        continue
                    out.append(
                        {
                            "ip": ip,
                            "usuario": user,
                            "hostname": doc.get("hostname") or "unknown",
                            "desde": doc.get("ad_ultima_sync"),
                        }
                    )
            except Exception as e:
                logger.error("Error leyendo identities para logon fallback: %s", e)

        return out

    def _get_user_by_sam_sync(self, sam: str) -> Optional[Dict[str, Any]]:
        """Busca usuario por sAMAccountName (incluye deshabilitados)."""
        esc = escape_filter_chars((sam or "").strip())
        if not esc:
            return None
        filt = (
            "(&(objectClass=user)(objectCategory=person)(sAMAccountName=%s))" % esc
        )
        attrs = list(self.USER_ATTRIBUTES) + ["userAccountControl"]
        rows = self._search_entries_sync(filt, attrs)
        if not rows:
            return None
        return rows[0]

    def _set_user_account_control_sync(self, dn: str, uac: int) -> tuple[bool, str]:
        if not dn:
            return False, "dn_vacio"
        if not self._ensure_bound_sync():
            return False, "bind_failed"
        assert self._conn is not None
        ok = self._conn.modify(
            str(dn),
            {"userAccountControl": [(MODIFY_REPLACE, [str(int(uac))])]},
        )
        if not ok:
            return False, str(self._conn.result)
        return True, ""

    async def get_user_by_sam(self, sam: str) -> Optional[Dict[str, Any]]:
        def _run() -> Optional[Dict[str, Any]]:
            return self._get_user_by_sam_sync(sam)

        return await asyncio.to_thread(_run)

    async def set_user_account_control(self, dn: str, uac: int) -> tuple[bool, str]:
        def _run() -> tuple[bool, str]:
            return self._set_user_account_control_sync(dn, uac)

        return await asyncio.to_thread(_run)

    def close(self) -> None:
        self._close_sync()
