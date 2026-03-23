"""
CONTRATO DE EVENTOS WEBSOCKET — NYXAR
Fuente de verdad de los nombres socket.io entre api/websocket.py y dashboard.

Cualquier cambio aquí debe reflejarse en ambos lados.
"""

from typing import Any, Dict

# --- Eventos que el SERVER emite al CLIENT (pipeline y alertas) ---

SERVER_EVENTS: Dict[str, str] = {
    "new_event": "Nuevo evento enriquecido del pipeline",
    "new_alert": "Nuevo incidente detectado por el correlator",
    "honeypot_hit": "Activación de un honeypot interno",
    "identity_update": "Cambio de risk_score de una identidad",
    "ai_memo": "Nuevo análisis generado por Claude",
    "stats_update": "Actualización de estadísticas generales (cada 30s)",
    "health_update": "Estado de salud del sistema (cada 60s)",
    "response_proposal": "Nueva propuesta de acción automatizada",
}

# Bootstrap, batches y métricas extra (mismo criterio de nombres snake_case)
SERVER_EVENTS_SUPPLEMENTAL: Dict[str, str] = {
    "initial_state": "Snapshot al conectar (eventos, identidades, memos)",
    "new_event_batch": "Hasta 20 eventos agrupados (rate limit)",
    "health_throughput": "Serie eventos/min para gráficos (cada 30s)",
    "pong": "Respuesta al ping del cliente (keepalive)",
}

# --- Eventos que el CLIENT envía al SERVER ---

CLIENT_EVENTS: Dict[str, str] = {
    "subscribe_identity": "Cliente quiere recibir todos los eventos de una identidad",
    "unsubscribe_identity": "Cliente deja de seguir una identidad",
    "request_ceo_view": "Cliente solicita análisis CEO",
    "ping": "Keepalive desde el cliente",
}

# --- Payload orientativo (documentación / validación futura) ---

EVENT_PAYLOADS: Dict[str, Dict[str, Any]] = {
    "new_event": {
        "schema": "Evento completo serializado como dict",
        "example": {"id": "evt_...", "source": "dns", "risk_score": 45, "...": "..."},
    },
    "new_alert": {
        "schema": "Incidente completo serializado como dict",
        "example": {"id": "inc_...", "titulo": "...", "severidad": "critica"},
    },
    "honeypot_hit": {
        "schema": "HoneypotHit completo serializado como dict",
        "example": {"id": "hp_...", "recurso": "BACKUP_FINANCIERO_2025", "ip_interna": "..."},
    },
    "identity_update": {
        "schema": "Dict con id, risk_score actual y delta",
        "example": {"identidad_id": "ventas.garcia", "risk_score": 67, "delta": 12},
    },
    "ai_memo": {
        "schema": "AiMemo completo serializado como dict",
        "example": {"id": "memo_...", "tipo": "autonomo", "prioridad": "alta", "contenido": "..."},
    },
    "stats_update": {
        "schema": "Dict con estadísticas del pipeline",
        "example": {"eventos_por_min": 14.5, "identidades_activas": 12, "alertas_abiertas": 2},
    },
}

# --- Constantes para el server (evitar typos; deben coincidir con las keys anteriores) ---

NEW_EVENT = "new_event"
NEW_ALERT = "new_alert"
HONEYPOT_HIT = "honeypot_hit"
IDENTITY_UPDATE = "identity_update"
AI_MEMO = "ai_memo"
STATS_UPDATE = "stats_update"
HEALTH_UPDATE = "health_update"
RESPONSE_PROPOSAL = "response_proposal"

INITIAL_STATE = "initial_state"
NEW_EVENT_BATCH = "new_event_batch"
HEALTH_THROUGHPUT = "health_throughput"
PONG = "pong"

SUBSCRIBE_IDENTITY = "subscribe_identity"
UNSUBSCRIBE_IDENTITY = "unsubscribe_identity"
REQUEST_CEO_VIEW = "request_ceo_view"
PING = "ping"
