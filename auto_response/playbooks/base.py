"""Contrato común de playbooks de ejecución."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict

from auto_response.models import AccionPropuesta


class PlaybookBase(ABC):
    nombre: str

    @abstractmethod
    async def execute(
        self,
        accion: AccionPropuesta,
        contexto: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Ejecuta la acción y devuelve dict serializable:
        exito: bool, detalle: str, payload_redactado: opcional
        """
        raise NotImplementedError
