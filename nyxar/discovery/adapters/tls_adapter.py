"""
TLS / CA interna (D05): contexto SSL y kwargs httpx sin desactivar verify.
"""

from __future__ import annotations

import logging
import ssl
from pathlib import Path
from typing import Any

from nyxar.discovery.engine import InfrastructureMap

logger = logging.getLogger("nyxar.discovery.adapters.tls")


class TlsAdapter:
    """
    Ajusta confianza SSL segun InfrastructureMap (CA interna detectada o manual).
    Nunca usa verify=False.
    """

    def __init__(self, infra: InfrastructureMap) -> None:
        self.infra = infra

    def get_ssl_context(self) -> ssl.SSLContext:
        context = ssl.create_default_context()
        path = self._resolved_ca_path()
        if path is None:
            return context
        p = Path(path)
        try:
            if p.is_file():
                context.load_verify_locations(cafile=str(p))
            elif p.is_dir():
                context.load_verify_locations(capath=str(p))
            else:
                return ssl.create_default_context()
        except OSError as e:
            logger.warning("No se pudo cargar CA en contexto SSL: %s", e)
            return ssl.create_default_context()
        logger.info("Contexto SSL con CA adicional: %s", path)
        return context

    def get_httpx_client_kwargs(self) -> dict[str, Any]:
        path = self._resolved_ca_path()
        if path:
            return {"verify": path}
        if self.infra.tls_inspection:
            logger.warning(
                "Inspeccion TLS en proxy pero sin ruta de CA interna. "
                "Configura NYXAR_CA_CERT_PATH con el PEM de la CA corporativa. "
                "No se desactiva la verificacion SSL."
            )
        return {"verify": True}

    def _resolved_ca_path(self) -> str | None:
        raw = (self.infra.ca_cert_path or "").strip()
        if not raw:
            return None
        p = Path(raw)
        return str(p.resolve()) if p.exists() else None


def suggest_tls_env(infra: InfrastructureMap) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if infra.ca_cert_path:
        p = infra.ca_cert_path
        out["NYXAR_CA_CERT_PATH"] = p
        out["REQUESTS_CA_BUNDLE"] = p
        out["SSL_CERT_FILE"] = p
    return out
