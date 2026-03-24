"""
Salud de conexiones adaptativas (D10): comprobaciones periodicas y re-discovery parcial.
Redis opcional: alertas via STREAM_ALERTS y huella de CA en cache.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import os
import socket
from typing import Any, Optional
from urllib.parse import urlparse

from nyxar.discovery.engine import DiscoveryEngine, InfrastructureMap

logger = logging.getLogger("nyxar.discovery.connection_health")

CA_FINGERPRINT_CACHE_KEY = "nyxar:discovery:ca_cert_fingerprint"
DEFAULT_ALERT_STREAM = "events:alerts"


class ConnectionChangedError(Exception):
    """Cambio detectado en un componente de infraestructura."""

    def __init__(self, component: str, description: str) -> None:
        super().__init__(description)
        self.component = component
        self.description = description


class AdaptiveConnectionHealth:
    """
    Verifica DNS, proxy, Wazuh y certificado CA; opcionalmente publica alertas y re-ejecuta probes.
    """

    def __init__(
        self,
        infra: InfrastructureMap,
        redis_bus: Optional[Any] = None,
        *,
        check_interval_s: float = 300.0,
        rediscovery_interval_s: float = 86400.0,
        tcp_timeout_s: float = 3.0,
        alert_stream: Optional[str] = None,
    ) -> None:
        self.infra = infra
        self.redis_bus = redis_bus
        self.check_interval_s = check_interval_s
        self.rediscovery_interval_s = rediscovery_interval_s
        self.tcp_timeout_s = tcp_timeout_s
        self._alert_stream = alert_stream or os.environ.get(
            "NYXAR_DISCOVERY_ALERT_STREAM", DEFAULT_ALERT_STREAM
        )
        self._stop = asyncio.Event()

    def stop(self) -> None:
        self._stop.set()

    async def start(self) -> None:
        """Bucle de chequeos periodicos y re-discovery completo diario (ambos en paralelo)."""
        await asyncio.gather(
            self._periodic_checks(),
            self._daily_rediscovery(),
        )

    async def run_until_stopped(self) -> None:
        """Igual que start; nombre explicito para procesos largos."""
        await self.start()

    async def _periodic_checks(self) -> None:
        while not self._stop.is_set():
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=self.check_interval_s)
                break
            except asyncio.TimeoutError:
                pass
            await self._check_all()

    async def _daily_rediscovery(self) -> None:
        while not self._stop.is_set():
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=self.rediscovery_interval_s)
                break
            except asyncio.TimeoutError:
                pass
            try:
                await DiscoveryEngine().run_full_discovery(
                    network_hint=self.infra.network_range,
                    verbose=False,
                    seed=self.infra,
                )
                logger.info("Re-discovery periodico completado")
            except Exception as e:
                logger.warning("Re-discovery periodico fallo: %s", e)

    async def _check_all(self) -> None:
        checks: list[asyncio.Task[Any]] = []

        if self.infra.dns_server:
            checks.append(asyncio.create_task(self._check_dns(self.infra)))

        if self.infra.proxy_present and self.infra.proxy_host and self.infra.proxy_port:
            checks.append(asyncio.create_task(self._check_proxy(self.infra)))

        if self.infra.wazuh_present and self.infra.wazuh_api_url:
            checks.append(asyncio.create_task(self._check_wazuh(self.infra)))

        if self.infra.ca_cert_path:
            checks.append(asyncio.create_task(self._check_ca_cert(self.infra)))

        if not checks:
            return

        results = await asyncio.gather(*checks, return_exceptions=True)
        for result in results:
            if isinstance(result, ConnectionChangedError):
                await self._handle_connection_changed(result)

    async def _handle_connection_changed(self, err: ConnectionChangedError) -> None:
        logger.warning(
            "Cambio de infraestructura: %s — %s",
            err.component,
            err.description,
        )
        await self._publish_alert(
            {
                "tipo": "infrastructure_change",
                "data": {
                    "component": err.component,
                    "change": err.description,
                    "action": "re_discovery_triggered",
                },
            }
        )
        await self._rediscover_component(err.component, self.infra)
        DiscoveryEngine()._save_map(self.infra)

    async def _publish_alert(self, payload: dict[str, Any]) -> None:
        bus = self.redis_bus
        if bus is None:
            return
        try:
            if not bus.client:
                await bus.connect()
            stream = getattr(bus, "STREAM_ALERTS", self._alert_stream)
            await bus.publish_event(stream, payload)
        except Exception as e:
            logger.warning("No se pudo publicar alerta en Redis: %s", e)

    async def _cache_get(self, key: str) -> Optional[dict]:
        bus = self.redis_bus
        if bus is None:
            return None
        try:
            if not bus.client:
                await bus.connect()
            return await bus.cache_get(key)
        except Exception as e:
            logger.warning("Redis cache_get %s: %s", key, e)
            return None

    async def _cache_set(self, key: str, value: dict, ttl: int) -> None:
        bus = self.redis_bus
        if bus is None:
            return
        try:
            if not bus.client:
                await bus.connect()
            await bus.cache_set(key, value, ttl=ttl)
        except Exception as e:
            logger.warning("Redis cache_set %s: %s", key, e)

    async def _check_dns(self, infra: InfrastructureMap) -> None:
        if not infra.dns_server:
            return
        ok = await asyncio.to_thread(
            self._tcp_open,
            infra.dns_server,
            53,
        )
        if not ok:
            raise ConnectionChangedError(
                "dns",
                f"No responde TCP/53 en el DNS registrado ({infra.dns_server}).",
            )

    async def _check_proxy(self, infra: InfrastructureMap) -> None:
        host = infra.proxy_host or ""
        port = int(infra.proxy_port or 0)
        if not host or not port:
            return
        ok = await asyncio.to_thread(self._tcp_open, host, port)
        if not ok:
            raise ConnectionChangedError(
                "proxy",
                f"No responde el proxy en {host}:{port}.",
            )

    async def _check_wazuh(self, infra: InfrastructureMap) -> None:
        url = (infra.wazuh_api_url or "").strip()
        if not url:
            return
        parsed = urlparse(url if "://" in url else f"https://{url}")
        host = parsed.hostname
        port = parsed.port or (443 if parsed.scheme != "http" else 80)
        if not host:
            return
        ok = await asyncio.to_thread(self._tcp_open, host, port)
        if not ok:
            raise ConnectionChangedError(
                "wazuh",
                f"No responde el API Wazuh en {host}:{port}.",
            )

    async def _check_ca_cert(self, infra: InfrastructureMap) -> None:
        path = infra.ca_cert_path
        if not path:
            return
        try:

            def _read() -> bytes:
                with open(path, "rb") as f:
                    return f.read()

            cert_data = await asyncio.to_thread(_read)
        except FileNotFoundError as e:
            raise ConnectionChangedError(
                "tls_ca",
                f"No se encuentra el certificado de la CA: {e}",
            ) from e
        except PermissionError as e:
            raise ConnectionChangedError(
                "tls_ca",
                f"No se puede leer el certificado de la CA: {e}",
            ) from e

        current_fp = hashlib.sha256(cert_data).hexdigest()
        saved = await self._cache_get(CA_FINGERPRINT_CACHE_KEY)

        if not saved or not saved.get("fingerprint"):
            await self._cache_set(
                CA_FINGERPRINT_CACHE_KEY,
                {"fingerprint": current_fp},
                ttl=86400 * 30,
            )
            return

        if saved.get("fingerprint") != current_fp:
            await self._cache_set(
                CA_FINGERPRINT_CACHE_KEY,
                {"fingerprint": current_fp},
                ttl=86400 * 30,
            )
            raise ConnectionChangedError(
                "tls_ca",
                "El certificado de la CA interna cambio (huella distinta).",
            )

    def _tcp_open(self, host: str, port: int) -> bool:
        try:
            with socket.create_connection((host, port), timeout=self.tcp_timeout_s):
                return True
        except OSError:
            return False

    async def _rediscover_component(self, component: str, infra: InfrastructureMap) -> None:
        from nyxar.discovery.probes.dns_probe import DnsProbe
        from nyxar.discovery.probes.proxy_probe import ProxyProbe
        from nyxar.discovery.probes.tls_probe import TlsProbe
        from nyxar.discovery.probes.wazuh_probe import WazuhProbe

        try:
            if component == "dns":
                await DnsProbe(infra).run()
            elif component == "proxy":
                await ProxyProbe(infra).run()
            elif component == "wazuh":
                await WazuhProbe(infra).run()
            elif component == "tls_ca":
                await TlsProbe(infra).run()
            else:
                logger.info(
                    "Re-discovery parcial no definida para %s; mapa se actualizara en el siguiente ciclo.",
                    component,
                )
        except Exception as e:
            logger.warning("Re-discovery %s fallo: %s", component, e)


async def run_health_loop(
    infra: InfrastructureMap,
    redis_bus: Optional[Any] = None,
) -> None:
    """Punto de entrada para proceso dedicado (requiere REDIS_URL si se usa bus)."""
    health = AdaptiveConnectionHealth(infra, redis_bus=redis_bus)
    await health.start()
