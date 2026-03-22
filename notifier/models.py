from typing import Literal, Optional

from pydantic import BaseModel, Field


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
