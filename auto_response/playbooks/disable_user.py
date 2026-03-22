"""Deshabilitar usuario en Active Directory (PROMPTS_V2)."""

from __future__ import annotations

import os
import re
import uuid
from datetime import datetime, timezone
from typing import Any, List, Optional, Set

from ad_connector.client import ADClient, DISABLED_UAC_BIT
from ad_connector.resolver import IdentityResolver
from shared.logger import get_logger
from shared.mongo_client import MongoClient
from shared.redis_bus import RedisBus

from auto_response.models import PlaybookResult
from auto_response.playbook_collections import COL_AD_DISABLE_STATE
from auto_response.playbooks.base import BasePlaybook

logger = get_logger("auto_response.playbooks.disable_user")


def _infer_bind_sam_account() -> Optional[str]:
    """Intenta obtener sAMAccountName de la cuenta de enlace (CN= o UPN)."""
    bind = (os.getenv("AD_USER") or "").strip()
    if not bind:
        return None
    if "@" in bind:
        return bind.split("@", 1)[0].strip().lower()
    m = re.match(r"(?i)^CN=([^,=]+)", bind)
    if m:
        return m.group(1).strip().lower()
    return None


def _member_of_list(member_of: Any) -> List[str]:
    if member_of is None:
        return []
    if isinstance(member_of, str):
        return [member_of]
    try:
        return [str(x) for x in member_of]
    except TypeError:
        return []


def _is_domain_admin(member_of: Any) -> bool:
    for g in _member_of_list(member_of):
        if "domain admins" in (g or "").lower():
            return True
    return False


def _parse_uac(raw: Any) -> int:
    try:
        if isinstance(raw, (list, tuple)) and raw:
            raw = raw[0]
        return int(raw)
    except (TypeError, ValueError):
        return 0


async def _collect_ips_for_user(mongo: MongoClient, sam: str) -> Set[str]:
    ips: Set[str] = set()
    db = mongo.db
    if db is None or not sam:
        return ips
    pattern = re.compile(f"^{re.escape(sam.strip())}$", re.IGNORECASE)
    try:
        async for d in db.wazuh_logons.find({"usuario": pattern}):
            ip = d.get("ip")
            if ip:
                ips.add(str(ip))
    except Exception as e:
        logger.warning("disable_user wazuh_logons scan: %s", e)
    try:
        async for d in db.identities.find({"usuario": pattern}):
            ip = d.get("ip_asociada")
            if ip:
                ips.add(str(ip))
    except Exception as e:
        logger.warning("disable_user identities scan: %s", e)
    return ips


async def _invalidate_sessions(
    mongo: MongoClient,
    redis_bus: RedisBus,
    sam: str,
) -> None:
    if not redis_bus:
        return
    resolver = IdentityResolver(redis_bus, mongo)
    for ip in await _collect_ips_for_user(mongo, sam):
        await resolver.invalidate(ip)


class DisableUserPlaybook(BasePlaybook):
    nombre = "Deshabilitar usuario en AD"
    descripcion = "Establece ACCOUNTDISABLE en userAccountControl vía LDAP."
    reversible = True

    def __init__(
        self,
        mongo: Optional[MongoClient] = None,
        redis_bus: Optional[RedisBus] = None,
    ) -> None:
        self.mongo = mongo
        self.redis_bus = redis_bus

    async def check_preconditions(self, objetivo: str) -> tuple[bool, str]:
        sam = (objetivo or "").strip()
        if not sam:
            return False, "sAMAccountName vacio."

        enabled = os.getenv("AD_WRITE_ENABLED", "").strip().lower() in (
            "1",
            "true",
            "yes",
        )
        if not enabled:
            return False, "AD_WRITE_ENABLED=false; no se permiten escrituras LDAP."

        client = ADClient(mongo_client=self.mongo)
        try:
            if not client.is_configured():
                return False, "AD no configurado (AD_SERVER, AD_BASE_DN, AD_USER, AD_PASSWORD)."

            svc = (os.getenv("NYXAR_SERVICE_ACCOUNT_SAM") or "").strip().lower()
            if svc and sam.lower() == svc:
                return False, "Cuenta de servicio NYXAR protegida; no deshabilitar."

            bind_sam = _infer_bind_sam_account()
            if bind_sam and sam.lower() == bind_sam:
                return False, "No deshabilitar la cuenta de enlace LDAP (AD_USER)."

            try:
                user = await client.get_user_by_sam(sam)
            except Exception as e:
                logger.warning("disable_user LDAP lectura precondiciones: %s", e)
                return False, f"No se pudo consultar AD: {e}"

            if not user:
                return False, "Usuario no existe en AD."

            if _is_domain_admin(user.get("memberOf")):
                return (
                    False,
                    "Usuario miembro de Domain Admins; no se deshabilita automaticamente.",
                )

            return True, ""
        finally:
            try:
                client.close()
            except Exception:
                pass

    async def execute_core(
        self,
        objetivo: str,
        incident_id: str,
        ejecutado_by: str,
    ) -> PlaybookResult:
        sam = (objetivo or "").strip()
        now = datetime.now(timezone.utc)
        execution_id = str(uuid.uuid4())
        client = ADClient(mongo_client=self.mongo)
        try:
            user = await client.get_user_by_sam(sam)
        except Exception as e:
            logger.warning("disable_user LDAP lectura: %s", e)
            try:
                client.close()
            except Exception:
                pass
            return PlaybookResult(
                execution_id=execution_id,
                playbook=self.nombre,
                objetivo=sam,
                exitoso=False,
                mensaje=str(e),
                detalles={"fase": "ldap_read"},
                ejecutado_at=now,
                puede_deshacer=False,
            )

        try:
            if not user:
                return PlaybookResult(
                    execution_id=execution_id,
                    playbook=self.nombre,
                    objetivo=sam,
                    exitoso=False,
                    mensaje="Usuario no encontrado.",
                    detalles={},
                    ejecutado_at=now,
                    puede_deshacer=False,
                )

            if _is_domain_admin(user.get("memberOf")):
                return PlaybookResult(
                    execution_id=execution_id,
                    playbook=self.nombre,
                    objetivo=sam,
                    exitoso=False,
                    mensaje="Domain Admin; accion abortada.",
                    detalles={},
                    ejecutado_at=now,
                    puede_deshacer=False,
                )

            dn = user.get("distinguishedName")
            if not dn:
                return PlaybookResult(
                    execution_id=execution_id,
                    playbook=self.nombre,
                    objetivo=sam,
                    exitoso=False,
                    mensaje="Sin distinguishedName en AD.",
                    detalles={},
                    ejecutado_at=now,
                    puede_deshacer=False,
                )

            prev_uac = _parse_uac(user.get("userAccountControl"))
            if prev_uac & DISABLED_UAC_BIT:
                return PlaybookResult(
                    execution_id=execution_id,
                    playbook=self.nombre,
                    objetivo=sam,
                    exitoso=True,
                    mensaje="Usuario ya deshabilitado (idempotente).",
                    detalles={"userAccountControl": prev_uac},
                    ejecutado_at=now,
                    puede_deshacer=False,
                )

            new_uac = prev_uac | DISABLED_UAC_BIT
            ok, err = await client.set_user_account_control(str(dn), new_uac)
            if not ok:
                logger.warning("disable_user LDAP modify fallo: %s", err)
                return PlaybookResult(
                    execution_id=execution_id,
                    playbook=self.nombre,
                    objetivo=sam,
                    exitoso=False,
                    mensaje=f"LDAP modify fallo: {err}",
                    detalles={},
                    ejecutado_at=now,
                    puede_deshacer=False,
                )

            db = self.mongo.db if self.mongo else None
            if db is not None:
                try:
                    await db[COL_AD_DISABLE_STATE].insert_one(
                        {
                            "execution_id": execution_id,
                            "sam": sam,
                            "dn": str(dn),
                            "prev_user_account_control": prev_uac,
                            "incident_id": incident_id,
                            "ejecutado_by": ejecutado_by,
                            "activo": True,
                            "creado_at": now,
                        }
                    )
                except Exception as e:
                    logger.warning("disable_user Mongo estado: %s", e)

            if self.mongo and self.redis_bus:
                try:
                    await _invalidate_sessions(self.mongo, self.redis_bus, sam)
                except Exception as e:
                    logger.warning("disable_user invalidar sesiones: %s", e)

            return PlaybookResult(
                execution_id=execution_id,
                playbook=self.nombre,
                objetivo=sam,
                exitoso=True,
                mensaje="Usuario deshabilitado en AD.",
                detalles={
                    "userAccountControl_antes": prev_uac,
                    "userAccountControl_despues": new_uac,
                },
                ejecutado_at=now,
                puede_deshacer=True,
            )
        finally:
            try:
                client.close()
            except Exception:
                pass

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
        doc = await db[COL_AD_DISABLE_STATE].find_one({"execution_id": execution_id})
        if not doc or not doc.get("activo"):
            return PlaybookResult(
                execution_id=execution_id,
                playbook=self.nombre,
                objetivo="",
                exitoso=False,
                mensaje="No hay deshabilitacion activa para ese execution_id",
                detalles={},
                ejecutado_at=now,
                puede_deshacer=False,
            )
        dn = str(doc.get("dn") or "")
        prev = int(doc.get("prev_user_account_control") or 0)
        sam = str(doc.get("sam") or "")
        client = ADClient(mongo_client=self.mongo)
        ok, err = await client.set_user_account_control(dn, prev)
        try:
            client.close()
        except Exception:
            pass
        if not ok:
            logger.warning("disable_user undo LDAP: %s", err)
            return PlaybookResult(
                execution_id=execution_id,
                playbook=self.nombre,
                objetivo=sam,
                exitoso=False,
                mensaje=f"LDAP undo fallo: {err}",
                detalles={},
                ejecutado_at=now,
                puede_deshacer=True,
            )
        await db[COL_AD_DISABLE_STATE].update_one(
            {"execution_id": execution_id},
            {"$set": {"activo": False, "restaurado_at": now.isoformat()}},
        )
        return PlaybookResult(
            execution_id=execution_id,
            playbook=self.nombre,
            objetivo=sam,
            exitoso=True,
            mensaje="userAccountControl restaurado.",
            detalles={"userAccountControl": prev},
            ejecutado_at=now,
            puede_deshacer=False,
        )
