"""Motor de respuesta automatizada asistida (SOAR) — propone; el humano aprueba."""

from auto_response.models import AccionPropuesta, ResponsePlan

__all__ = ["AccionPropuesta", "ResponsePlan", "ResponseEngine"]


def __getattr__(name: str):
    if name == "ResponseEngine":
        from auto_response.engine import ResponseEngine

        return ResponseEngine
    raise AttributeError(name)
