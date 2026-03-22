"""Bloqueo de IP externa en firewall perimetral + blocklist Redis (PROMPTS_V2)."""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import httpx

from shared.ip_utils import firewall_url, is_protected_ip, is_rfc1918, normalize_ip
from shared.logger import get_logger
from shared.mongo_client import MongoClient
from shared.redis_bus import RedisBus

from auto_response.models import PlaybookResult
from auto_response.playbook_collections import BLOCKLIST_NYXAR_EXTERNAL, COL_BLOCK_IP_STATE
from auto_response.playbooks.base import BasePlaybook

logger = get_logger("auto_response.playbooks.block_ip")


def _firewall_headers() -> Dict[str, str]:
    token = (os.getenv("FIREWALL_API_TOKEN") or "").strip()
    if not token:
        return {}
    return {"Authorization": f"Bearer {token}"}


class BlockIPPlaybook(BasePlaybook):
    nombre = "Bloqueo de IP externa"
    descripcion = "Bloquea una IP externa en el firewall y la marca en blocklist local."
    reversible = True

    def __init__(
        self,
        mongo: Optional[MongoClient] = None,
        redis_bus: Optional[RedisBus] = None,
    ) -> None:
        self.mongo = mongo
        self.redis_bus = redis_bus

    async def check_preconditions(self, objetivo: str) -> tuple[bool, str]:
        ip = normalize_ip(objetivo)
        if not ip:
            return False, "Objetivo no es una IP valida."
        if is_rfc1918(ip):
            return (
                False,
                "IP interna detectada; use el playbook de cuarentena en lugar de bloqueo externo.",
            )
        if is_protected_ip(ip):
            return False, "IP en PROTECTED_IPS; accion no permitida."
        return True, ""

    async def execute_core(
        self,
        objetivo: str,
        incident_id: str,
        ejecutado_by: str,
    ) -> PlaybookResult:
        ip = normalize_ip(objetivo) or objetivo.strip()
        now = datetime.now(timezone.utc)
        execution_id = str(uuid.uuid4())
        base = (os.getenv("FIREWALL_API_URL") or "").strip()

        on_blocklist = False
        if self.redis_bus and self.redis_bus.client:
            try:
                on_blocklist = await self.redis_bus.blocklist_check(
                    BLOCKLIST_NYXAR_EXTERNAL,
                    ip,
                )
            except Exception as e:
                logger.warning("BlockIPPlaybook blocklist_check: %s", e)

        db = self.mongo.db if self.mongo else None
        doc: Optional[Dict[str, Any]] = None
        mongo_active = False
        if db is not None:
            doc = await db[COL_BLOCK_IP_STATE].find_one({"ip": ip, "activo": True})
            mongo_active = doc is not None

        if on_blocklist and mongo_active:
            eid = str(doc.get("execution_id") or "") if doc else ""
            return PlaybookResult(
                execution_id=eid or execution_id,
                playbook=self.nombre,
                objetivo=ip,
                exitoso=True,
                mensaje="IP ya bloqueada (idempotente).",
                detalles={"idempotente": True},
                ejecutado_at=now,
                puede_deshacer=bool(eid),
            )

        if on_blocklist and not base:
            if db is not None and not mongo_active:
                try:
                    await db[COL_BLOCK_IP_STATE].insert_one(
                        {
                            "execution_id": execution_id,
                            "ip": ip,
                            "incident_id": incident_id,
                            "ejecutado_by": ejecutado_by,
                            "activo": True,
                            "solo_redis": True,
                            "creado_at": now,
                        }
                    )
                except Exception as e:
                    logger.warning("BlockIPPlaybook persistencia Mongo: %s", e)
            return PlaybookResult(
                execution_id=execution_id,
                playbook=self.nombre,
                objetivo=ip,
                exitoso=True,
                mensaje="IP ya en blocklist local; firewall no configurado.",
                detalles={"solo_blocklist": True},
                ejecutado_at=now,
                puede_deshacer=True,
            )

        if not base:
            return PlaybookResult(
                execution_id="",
                playbook=self.nombre,
                objetivo=ip,
                exitoso=False,
                mensaje="Firewall API no disponible. Accion manual requerida.",
                detalles={"fase": "config"},
                ejecutado_at=now,
                puede_deshacer=False,
            )

        url = firewall_url(base, "rules/block_external")
        body = {
            "ip": ip,
            "direction": "both",
            "comment": f"NYXAR: Incidente {incident_id}",
        }
        regla_id: Optional[str] = None
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                r = await client.post(
                    url,
                    json=body,
                    headers=_firewall_headers(),
                )
            ok = 200 <= r.status_code < 300
            if ok:
                try:
                    data = r.json()
                    if isinstance(data, dict):
                        rid = data.get("id") or data.get("rule_id")
                        if rid is not None:
                            regla_id = str(rid)
                except (json.JSONDecodeError, TypeError, ValueError):
                    regla_id = None
            if not ok:
                logger.warning(
                    "BlockIPPlaybook firewall HTTP %s: %s",
                    r.status_code,
                    (r.text or "")[:500],
                )
                return PlaybookResult(
                    execution_id=execution_id,
                    playbook=self.nombre,
                    objetivo=ip,
                    exitoso=False,
                    mensaje=f"Firewall rechazo el bloqueo: HTTP {r.status_code}",
                    detalles={"http_status": r.status_code},
                    ejecutado_at=now,
                    puede_deshacer=False,
                )
        except Exception as e:
            logger.warning("BlockIPPlaybook error firewall: %s", e)
            return PlaybookResult(
                execution_id=execution_id,
                playbook=self.nombre,
                objetivo=ip,
                exitoso=False,
                mensaje=str(e),
                detalles={"fase": "firewall_http"},
                ejecutado_at=now,
                puede_deshacer=False,
            )

        if self.redis_bus and self.redis_bus.client:
            try:
                await self.redis_bus.blocklist_add(BLOCKLIST_NYXAR_EXTERNAL, ip)
            except Exception as e:
                logger.warning("BlockIPPlaybook blocklist_add: %s", e)

        if db is not None:
            try:
                await db[COL_BLOCK_IP_STATE].insert_one(
                    {
                        "execution_id": execution_id,
                        "ip": ip,
                        "regla_firewall_id": regla_id,
                        "incident_id": incident_id,
                        "ejecutado_by": ejecutado_by,
                        "activo": True,
                        "creado_at": now,
                    }
                )
            except Exception as e:
                logger.warning("BlockIPPlaybook Mongo insert: %s", e)

        return PlaybookResult(
            execution_id=execution_id,
            playbook=self.nombre,
            objetivo=ip,
            exitoso=True,
            mensaje="IP externa bloqueada en firewall y blocklist local.",
            detalles={"regla_firewall_id": regla_id},
            ejecutado_at=now,
            puede_deshacer=True,
        )

    async def undo(self, execution_id: str) -> PlaybookResult:
        now = datetime.now(timezone.utc)
        if not execution_id:
            return PlaybookResult(
                execution_id="",
                playbook=self.nombre,
                objetivo="",
                exitoso=False,
                mensaje="execution_id vacio",
                detalles={},
                ejecutado_at=now,
                puede_deshacer=False,
            )
        db = self.mongo.db if self.mongo else None
        if db is None:
            return PlaybookResult(
                execution_id=execution_id,
                playbook=self.nombre,
                objetivo="",
                exitoso=False,
                mensaje="MongoDB no disponible",
                detalles={},
                ejecutado_at=now,
                puede_deshacer=False,
            )
        doc = await db[COL_BLOCK_IP_STATE].find_one({"execution_id": execution_id})
        if not doc or not doc.get("activo"):
            return PlaybookResult(
                execution_id=execution_id,
                playbook=self.nombre,
                objetivo="",
                exitoso=False,
                mensaje="No hay bloqueo activo para ese execution_id",
                detalles={},
                ejecutado_at=now,
                puede_deshacer=False,
            )
        ip = str(doc.get("ip") or "")
        regla_id = doc.get("regla_firewall_id")
        base = (os.getenv("FIREWALL_API_URL") or "").strip()
        removed = True
        if base and regla_id:
            try:
                del_url = firewall_url(base, f"rules/block_external/{regla_id}")
                async with httpx.AsyncClient(timeout=15.0) as client:
                    r = await client.delete(del_url, headers=_firewall_headers())
                removed = r.status_code in (200, 202, 204)
                if not removed:
                    rel = firewall_url(base, "rules/block_external/release")
                    async with httpx.AsyncClient(timeout=15.0) as client:
                        r2 = await client.post(
                            rel,
                            json={"id": regla_id, "ip": ip},
                            headers=_firewall_headers(),
                        )
                    removed = 200 <= r2.status_code < 300
            except Exception as e:
                logger.warning("BlockIPPlaybook undo API: %s", e)
                removed = False
        elif base and not regla_id:
            try:
                rel = firewall_url(base, "rules/block_external/release")
                async with httpx.AsyncClient(timeout=15.0) as client:
                    r3 = await client.post(
                        rel,
                        json={"ip": ip},
                        headers=_firewall_headers(),
                    )
                removed = 200 <= r3.status_code < 300
            except Exception as e:
                logger.warning("BlockIPPlaybook undo API: %s", e)
                removed = False

        if self.redis_bus and self.redis_bus.client and ip:
            try:
                await self.redis_bus.blocklist_remove(BLOCKLIST_NYXAR_EXTERNAL, ip)
            except Exception as e:
                logger.warning("BlockIPPlaybook blocklist_remove: %s", e)

        if base and not removed:
            return PlaybookResult(
                execution_id=execution_id,
                playbook=self.nombre,
                objetivo=ip,
                exitoso=False,
                mensaje="API de firewall no confirmo el desbloqueo.",
                detalles={},
                ejecutado_at=now,
                puede_deshacer=True,
            )

        await db[COL_BLOCK_IP_STATE].update_one(
            {"execution_id": execution_id},
            {"$set": {"activo": False, "liberado_at": now.isoformat()}},
        )
        return PlaybookResult(
            execution_id=execution_id,
            playbook=self.nombre,
            objetivo=ip,
            exitoso=True,
            mensaje="Bloqueo revertido.",
            detalles={},
            ejecutado_at=now,
            puede_deshacer=False,
        )
