"""Cuarentena de dispositivo: IP interna + API firewall (PROMPTS_V2)."""

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
from auto_response.playbook_collections import COL_QUARANTINE_STATE
from auto_response.playbooks.base import BasePlaybook

logger = get_logger("auto_response.playbooks.quarantine")


def _firewall_headers() -> Dict[str, str]:
    token = (os.getenv("FIREWALL_API_TOKEN") or "").strip()
    if not token:
        return {}
    return {"Authorization": f"Bearer {token}"}


class QuarantinePlaybook(BasePlaybook):
    nombre = "Cuarentena de dispositivo"
    descripcion = "Aisla un dispositivo bloqueando su IP en firewall (y switch opcional)."
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
        if not is_rfc1918(ip):
            return False, "La cuarentena aplica solo a IPs internas (RFC1918). Use bloqueo de IP externa para el resto."
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
        base = (os.getenv("FIREWALL_API_URL") or "").strip()
        if not base:
            return PlaybookResult(
                execution_id="",
                playbook=self.nombre,
                objetivo=ip,
                exitoso=False,
                mensaje="Firewall API no disponible. Accion manual requerida.",
                detalles={"fase": "config"},
                ejecutado_at=datetime.now(timezone.utc),
                puede_deshacer=False,
            )

        execution_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)

        db = self.mongo.db if self.mongo else None
        if db is not None:
            existing = await db[COL_QUARANTINE_STATE].find_one(
                {"ip": ip, "activo": True},
            )
            if existing:
                eid = str(existing.get("execution_id") or "")
                return PlaybookResult(
                    execution_id=eid,
                    playbook=self.nombre,
                    objetivo=ip,
                    exitoso=True,
                    mensaje="Cuarentena ya activa (idempotente).",
                    detalles={
                        "regla_firewall_id": existing.get("regla_firewall_id"),
                        "prev_execution_id": eid,
                    },
                    ejecutado_at=now,
                    puede_deshacer=self.reversible and bool(eid),
                )

        url = firewall_url(base, "rules/quarantine")
        body = {"ip": ip, "reason": f"Incidente {incident_id}"}
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
                        regla_id = (
                            data.get("id")
                            or data.get("regla_firewall_id")
                            or data.get("rule_id")
                        )
                        if regla_id is not None:
                            regla_id = str(regla_id)
                except (json.JSONDecodeError, TypeError, ValueError):
                    regla_id = None
            if not ok:
                logger.warning(
                    "QuarantinePlaybook firewall HTTP %s: %s",
                    r.status_code,
                    (r.text or "")[:500],
                )
                return PlaybookResult(
                    execution_id=execution_id,
                    playbook=self.nombre,
                    objetivo=ip,
                    exitoso=False,
                    mensaje=f"Firewall rechazo la cuarentena: HTTP {r.status_code}",
                    detalles={"http_status": r.status_code},
                    ejecutado_at=now,
                    puede_deshacer=False,
                )
        except Exception as e:
            logger.warning("QuarantinePlaybook error firewall: %s", e)
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

        switch_url = (os.getenv("SWITCH_API_URL") or "").strip()
        switch_ok: Optional[bool] = None
        if switch_url:
            try:
                sw = firewall_url(switch_url, "quarantine")
                async with httpx.AsyncClient(timeout=12.0) as client:
                    sr = await client.post(
                        sw,
                        json={
                            "ip": ip,
                            "action": "quarantine",
                            "reason": f"Incidente {incident_id}",
                        },
                        headers=_firewall_headers(),
                    )
                switch_ok = 200 <= sr.status_code < 300
                if not switch_ok:
                    logger.warning(
                        "QuarantinePlaybook switch HTTP %s",
                        sr.status_code,
                    )
            except Exception as e:
                switch_ok = False
                logger.warning("QuarantinePlaybook switch API: %s", e)

        if db is not None:
            doc: Dict[str, Any] = {
                "execution_id": execution_id,
                "ip": ip,
                "regla_firewall_id": regla_id,
                "cuarentena_inicio": now,
                "incident_id": incident_id,
                "ejecutado_by": ejecutado_by,
                "activo": True,
                "switch_intentado": bool(switch_url),
                "switch_ok": switch_ok,
            }
            try:
                await db[COL_QUARANTINE_STATE].insert_one(doc)
            except Exception as e:
                logger.warning("QuarantinePlaybook no pudo persistir estado Mongo: %s", e)

        detalles: Dict[str, Any] = {
            "regla_firewall_id": regla_id,
            "switch_ok": switch_ok,
        }
        return PlaybookResult(
            execution_id=execution_id,
            playbook=self.nombre,
            objetivo=ip,
            exitoso=True,
            mensaje="Cuarentena aplicada en firewall.",
            detalles=detalles,
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
                mensaje="MongoDB no disponible para undo",
                detalles={},
                ejecutado_at=now,
                puede_deshacer=False,
            )
        doc = await db[COL_QUARANTINE_STATE].find_one({"execution_id": execution_id})
        if not doc or not doc.get("activo"):
            return PlaybookResult(
                execution_id=execution_id,
                playbook=self.nombre,
                objetivo=str(doc.get("ip") if doc else ""),
                exitoso=False,
                mensaje="No hay cuarentena activa para ese execution_id",
                detalles={},
                ejecutado_at=now,
                puede_deshacer=False,
            )
        ip = str(doc.get("ip") or "")
        regla_id = doc.get("regla_firewall_id")
        base = (os.getenv("FIREWALL_API_URL") or "").strip()
        if not base:
            return PlaybookResult(
                execution_id=execution_id,
                playbook=self.nombre,
                objetivo=ip,
                exitoso=False,
                mensaje="Firewall API no configurada; undo manual requerido.",
                detalles={},
                ejecutado_at=now,
                puede_deshacer=False,
            )
        removed = False
        try:
            if regla_id:
                del_url = firewall_url(base, f"rules/quarantine/{regla_id}")
                async with httpx.AsyncClient(timeout=15.0) as client:
                    r = await client.delete(
                        del_url,
                        headers=_firewall_headers(),
                    )
                removed = r.status_code in (200, 202, 204)
                if not removed:
                    post_url = firewall_url(base, "rules/quarantine/release")
                    async with httpx.AsyncClient(timeout=15.0) as client:
                        r2 = await client.post(
                            post_url,
                            json={"id": regla_id, "ip": ip},
                            headers=_firewall_headers(),
                        )
                    removed = 200 <= r2.status_code < 300
            else:
                post_url = firewall_url(base, "rules/quarantine/release")
                async with httpx.AsyncClient(timeout=15.0) as client:
                    r3 = await client.post(
                        post_url,
                        json={"ip": ip},
                        headers=_firewall_headers(),
                    )
                removed = 200 <= r3.status_code < 300
        except Exception as e:
            logger.warning("QuarantinePlaybook undo API: %s", e)
            return PlaybookResult(
                execution_id=execution_id,
                playbook=self.nombre,
                objetivo=ip,
                exitoso=False,
                mensaje=str(e),
                detalles={"fase": "undo_http"},
                ejecutado_at=now,
                puede_deshacer=True,
            )
        if not removed:
            return PlaybookResult(
                execution_id=execution_id,
                playbook=self.nombre,
                objetivo=ip,
                exitoso=False,
                mensaje="API de firewall no confirmo la liberacion; revisar manualmente.",
                detalles={},
                ejecutado_at=now,
                puede_deshacer=True,
            )
        await db[COL_QUARANTINE_STATE].update_one(
            {"execution_id": execution_id},
            {
                "$set": {
                    "activo": False,
                    "cuarentena_fin": now.isoformat(),
                }
            },
        )
        return PlaybookResult(
            execution_id=execution_id,
            playbook=self.nombre,
            objetivo=ip,
            exitoso=True,
            mensaje="Cuarentena revertida en firewall.",
            detalles={},
            ejecutado_at=now,
            puede_deshacer=False,
        )
