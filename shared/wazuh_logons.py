"""
Persistencia minima de eventos de logon Wazuh en Mongo (coleccion wazuh_logons).
Evita tocar el schema de Evento; alimenta ADClient.get_logged_on_users.
"""

import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Set

from shared.logger import get_logger

logger = get_logger("shared.wazuh_logons")

_indexes_ready = False


def _rule_ids_from_env() -> Set[str]:
    raw = os.getenv("WAZUH_LOGON_RULE_IDS", "").strip()
    if not raw:
        return set()
    return {x.strip() for x in raw.split(",") if x.strip()}


def logon_rule_ids() -> Set[str]:
    return _rule_ids_from_env()


def _parse_wazuh_timestamp(ts_raw: Any) -> datetime:
    if isinstance(ts_raw, datetime):
        if ts_raw.tzinfo is None:
            return ts_raw.replace(tzinfo=timezone.utc)
        return ts_raw.astimezone(timezone.utc)
    if not ts_raw:
        return datetime.now(timezone.utc)
    s = str(ts_raw).strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except ValueError:
        return datetime.now(timezone.utc)


def extract_logon_document(payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Extrae ip, usuario, hostname y ts desde JSON nativo de Wazuh (defensivo).
    """
    rule = payload.get("rule") or {}
    rule_id = str(rule.get("id", "")).strip()
    if not rule_id:
        return None

    agent = payload.get("agent") or {}
    agent_ip = (agent.get("ip") or "").strip()
    hostname = (agent.get("name") or "").strip()

    data = payload.get("data") or {}
    win = data.get("win") or {}
    eventdata = win.get("eventdata") or {}

    usuario = (
        (eventdata.get("targetUserName") or "").strip()
        or (eventdata.get("subjectUserName") or "").strip()
    )

    system = win.get("system") or {}
    if not hostname:
        hostname = (system.get("computer") or "").strip()

    if not agent_ip:
        predecoder = data.get("predecoder") or {}
        agent_ip = (predecoder.get("hostname") or "").strip()

    ts = _parse_wazuh_timestamp(payload.get("timestamp"))

    if not agent_ip or agent_ip.lower() == "unknown":
        return None
    if not usuario:
        return None

    return {
        "rule_id": rule_id,
        "ip": agent_ip,
        "usuario": usuario,
        "hostname": hostname or "unknown",
        "ts": ts,
    }


async def ensure_wazuh_logons_indexes(db) -> None:
    """
    Crea indice TTL sobre created_at y compuesto ip+ts (idempotente por proceso).
    """
    global _indexes_ready
    if _indexes_ready:
        return

    ttl_s = int(os.getenv("WAZUH_LOGONS_TTL_SECONDS", "604800"))
    try:
        await db.wazuh_logons.create_index(
            [("created_at", 1)],
            expireAfterSeconds=ttl_s,
            name="wazuh_logons_created_ttl",
        )
    except Exception as e:
        logger.warning("No se pudo crear indice TTL wazuh_logons: %s", e)

    try:
        await db.wazuh_logons.create_index(
            [("ip", 1), ("ts", -1)],
            name="wazuh_logons_ip_ts",
        )
    except Exception as e:
        logger.warning("No se pudo crear indice compuesto wazuh_logons: %s", e)

    _indexes_ready = True


async def insert_wazuh_logon_if_applicable(db, payload: Dict[str, Any]) -> None:
    rule_ids = logon_rule_ids()
    if not rule_ids:
        return

    rule = payload.get("rule") or {}
    rid = str(rule.get("id", "")).strip()
    if rid not in rule_ids:
        return

    doc = extract_logon_document(payload)
    if not doc:
        return

    await ensure_wazuh_logons_indexes(db)
    doc["created_at"] = datetime.now(timezone.utc)
    try:
        await db.wazuh_logons.insert_one(doc)
    except Exception as e:
        logger.error("Fallo insert wazuh_logons: %s", e)
