from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class NotifMessage(BaseModel):
    """Contenido unificado para todos los canales (sin Slack en NYXAR)."""

    tipo: Literal["alerta", "reporte", "aprobacion", "resolucion"]
    severidad: str
    titulo: str
    cuerpo: str
    cuerpo_corto: str = ""
    link: Optional[str] = None
    incident_id: Optional[str] = None
    proposal_id: Optional[str] = None
    attachment_path: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    def short_for_whatsapp(self, max_len: int = 200) -> str:
        t = (self.cuerpo_corto or self.titulo or "").strip()
        if len(t) > max_len:
            return t[: max_len - 3] + "..."
        return t


class NotifPreferences(BaseModel):
    """Preferencias por destinatario (email y WhatsApp habilitados por defecto)."""

    email_enabled: bool = True
    whatsapp_enabled: bool = True


class Recipient(BaseModel):
    id: str
    nombre: str = ""
    email: Optional[str] = None
    whatsapp_number: Optional[str] = None
    area: Optional[str] = None
    es_admin: bool = False
    preferencias: NotifPreferences = Field(default_factory=NotifPreferences)


SeveridadNotif = Literal["critica", "alta", "media", "baja", "info"]
