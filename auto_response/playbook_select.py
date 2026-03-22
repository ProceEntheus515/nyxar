"""
Normaliza patron/severidad del correlator y construye un ResponsePlan ejecutable.
Las claves logicas internas no se persisten; solo el plan Pydantic.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Dict, FrozenSet, Literal, Optional, Set

from auto_response.models import AccionPropuesta, ResponsePlan


def normalize_severidad(incident: Dict[str, Any]) -> str:
    """CRITICA y CRÍTICA equivalentes (mayusculas, sin tilde)."""
    s = incident.get("severidad")
    if s is None:
        return ""
    return str(s).strip().upper().replace("Í", "I")


def classify_patron_keys(incident: Dict[str, Any]) -> FrozenSet[str]:
    """Subcadenas case-insensitive sobre patron + descripcion."""
    text = f"{incident.get('patron', '')} {incident.get('descripcion', '')}".lower()
    keys: Set[str] = set()
    if "beaconing" in text:
        keys.add("beaconing")
    if "movimiento lateral" in text or re.search(r"\blateral\b", text):
        keys.add("lateral_movement")
    if "exfil" in text or "volumen anormal" in text:
        keys.add("exfiltration")
    if "ransomware" in text:
        keys.add("ransomware")
    patron_u = str(incident.get("patron") or "").upper()
    if "TRAMPILLA_HONEYPOT" in patron_u or "honeypot" in text:
        keys.add("honeypot")
    return frozenset(keys)


def extract_usuario_from_incident(incident: Dict[str, Any]) -> Optional[str]:
    """Intenta resolver cuenta de usuario desde detalles u objetos anidados."""
    det = incident.get("detalles")
    if not isinstance(det, dict):
        return None
    for key in ("usuario", "user", "id_usuario", "user_id", "cuenta", "samaccountname"):
        val = det.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    interno = det.get("interno")
    if isinstance(interno, dict):
        for key in ("id_usuario", "usuario", "user"):
            val = interno.get(key)
            if isinstance(val, str) and val.strip():
                return val.strip()
    return None


def _accion(
    tipo: Literal["quarantine", "block_ip", "disable_user", "notify_only"],
    objetivo: str,
    descripcion: str,
    reversible: bool,
    impacto: str,
    requiere_aprobacion: bool = True,
) -> AccionPropuesta:
    return AccionPropuesta(
        tipo=tipo,
        objetivo=objetivo,
        descripcion=descripcion,
        reversible=reversible,
        impacto=impacto,
        requiere_aprobacion=requiere_aprobacion,
    )


def build_response_plan(incident: Dict[str, Any]) -> Optional[ResponsePlan]:
    """
    Devuelve None si no hay acciones automaticas recomendadas.
    """
    incident_id = str(incident.get("id") or "").strip()
    if not incident_id:
        return None

    sev = normalize_severidad(incident)
    keys = classify_patron_keys(incident)
    host = str(incident.get("host_afectado") or "").strip() or "unknown"

    acciones: list[AccionPropuesta] = []
    playbook_nombre = "default"
    justificacion = "Sin regla especifica; solo notificacion por severidad."
    urgencia: Any = "proxima_hora"

    if "honeypot" in keys:
        playbook_nombre = "honeypot_intrusion"
        usuario = extract_usuario_from_incident(incident)
        if usuario:
            acciones.append(
                _accion(
                    "disable_user",
                    usuario,
                    "Honeypot: posible uso de credencial; deshabilitar cuenta tras validacion.",
                    True,
                    "Alto: acceso a cuenta corporativa.",
                )
            )
        acciones.append(
            _accion(
                "notify_only",
                incident_id,
                "Notificar operadores: trampa honeypot activada.",
                True,
                "Bajo: solo visibilidad.",
                requiere_aprobacion=False,
            )
        )
        if not usuario and host and host != "unknown":
            acciones.append(
                _accion(
                    "block_ip",
                    host,
                    "Bloquear IP atacante detectada por honeypot (si aplica en perimetro).",
                    True,
                    "Medio: posible falso positivo si IP compartida.",
                )
            )
        justificacion = (
            "Patron honeypot: contencion del atacante y/o cuenta si es resoluble."
        )
        urgencia = "inmediata"

    elif sev == "CRITICA":
        urgencia = "inmediata"
        if "ransomware" in keys or "lateral_movement" in keys:
            playbook_nombre = "critical_containment"
            acciones.append(
                _accion(
                    "quarantine",
                    host,
                    "Aislar host en red (bloqueo IP del activo) por movimiento lateral o ransomware.",
                    False,
                    "Alto: interrupcion de servicio en ese host.",
                )
            )
            justificacion = "Severidad critica con patron de expansion o ransomware."
        acciones.append(
            _accion(
                "notify_only",
                incident_id,
                "Notificacion obligatoria en incidente critico.",
                True,
                "Bajo",
                requiere_aprobacion=False,
            )
        )
        if playbook_nombre == "default":
            playbook_nombre = "critical_notify"
            justificacion = "Severidad critica sin patron de cuarentena explicito; notificar."

    elif sev == "ALTA" and ("beaconing" in keys or "exfiltration" in keys):
        playbook_nombre = "high_network_response"
        acciones.append(
            _accion(
                "block_ip",
                host,
                "Bloqueo en perimetro del host implicado en beaconing o posible exfiltracion.",
                True,
                "Medio: revisar si el host es servidor legitimo.",
            )
        )
        acciones.append(
            _accion(
                "notify_only",
                incident_id,
                "Alertar al equipo SOC con contexto del incidente.",
                True,
                "Bajo",
                requiere_aprobacion=False,
            )
        )
        justificacion = "Alta severidad con comunicacion C2 o exfiltracion probable."
        urgencia = "proxima_hora"

    else:
        return None

    # Evitar duplicados exactos consecutivos (mismo tipo+objetivo)
    deduped: list[AccionPropuesta] = []
    seen: Set[tuple[str, str]] = set()
    for a in acciones:
        k = (a.tipo, a.objetivo)
        if k in seen:
            continue
        seen.add(k)
        deduped.append(a)

    if not deduped:
        return None

    return ResponsePlan(
        incident_id=incident_id,
        playbook_nombre=playbook_nombre,
        acciones=deduped,
        justificacion=justificacion,
        urgencia=urgencia,
    )


def incident_timestamp_utc(incident: Dict[str, Any]) -> Optional[datetime]:
    raw = incident.get("timestamp")
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


def is_candidate_incident(incident: Dict[str, Any]) -> bool:
    """Abierto o sin estado (correlator no siempre asigna estado)."""
    e = incident.get("estado")
    if e is None:
        return True
    s = str(e).strip().lower()
    return s == "" or s == "abierto"


def is_incident_recent(
    incident: Dict[str, Any],
    max_age_days: int,
) -> bool:
    if max_age_days <= 0:
        return True
    ts = incident_timestamp_utc(incident)
    if ts is None:
        return True
    delta = datetime.now(timezone.utc) - ts
    return delta.days <= max_age_days
