import logging
import ipaddress
from typing import Optional, Any
from datetime import datetime, timezone

from api.models import Evento, EventoInterno, EventoExterno
from shared.logger import get_logger
from shared.redis_bus import RedisBus

logger = get_logger("collector.normalizer")

class Normalizer:
    def __init__(self, redis_bus: RedisBus):
        self.redis_bus = redis_bus

    async def _resolver_hostname(self, ip: str) -> str:
        """Resuelve el hostname de una IP interna usando Redis."""
        key = f"identities:host:{ip}"
        data = await self.redis_bus.cache_get(key)
        if data and "hostname" in data:
            return data["hostname"]
        return "unknown"

    async def _resolver_usuario(self, ip: str) -> str:
        """Resuelve el usuario de una IP interna usando Redis."""
        key = f"identities:host:{ip}"
        data = await self.redis_bus.cache_get(key)
        if data and "usuario" in data:
            return data["usuario"]
        return "unknown"

    async def _resolver_area(self, ip: str) -> str:
        """Resuelve el área de una IP interna usando Redis."""
        key = f"identities:host:{ip}"
        data = await self.redis_bus.cache_get(key)
        if data and "area" in data:
            return data["area"]
        return "unknown"

    def _is_private_ip(self, ip_str: str) -> bool:
        try:
            ip = ipaddress.ip_address(ip_str)
            return ip.is_private
        except ValueError:
            return False

    def _parse_timestamp(self, ts_raw: Any) -> datetime:
        """
        Intenta parsear diferentes formatos de fecha/hora a datetime UTC.
        Si todos fallan, retorna datetime.now(timezone.utc).
        """
        if not ts_raw:
            return datetime.now(timezone.utc)
            
        # Unix timestamp
        if isinstance(ts_raw, (int, float)):
            try:
                return datetime.fromtimestamp(ts_raw, tz=timezone.utc)
            except Exception:
                pass
                
        ts_str = str(ts_raw).strip()
        
        # Si es un string numérico
        if ts_str.replace('.', '', 1).isdigit():
            try:
                return datetime.fromtimestamp(float(ts_str), tz=timezone.utc)
            except Exception:
                pass

        # Formatos comunes de texto
        formats = [
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%S.%f",
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M:%S.%f",
            "%d/%b/%Y:%H:%M:%S %z",
            "%b %d %H:%M:%S"
        ]

        for fmt in formats:
            try:
                dt = datetime.strptime(ts_str, fmt)
                # Si el formato no tiene año (ej: syslog), asumimos año actual
                if fmt == "%b %d %H:%M:%S":
                    dt = dt.replace(year=datetime.now(timezone.utc).year)
                # Si no tiene timezone, asumimos UTC
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except ValueError:
                continue

        logger.debug(f"Formato de fecha no reconocido: {ts_str}. Usando hora actual.")
        return datetime.now(timezone.utc)

    async def normalize(self, raw_log: dict, source: str) -> Optional[Evento]:
        """
        Punto de entrada principal.
        """
        try:
            if source == "dns":
                return await self._normalize_dns(raw_log)
            elif source == "proxy":
                return await self._normalize_proxy(raw_log)
            elif source == "firewall":
                return await self._normalize_firewall(raw_log)
            elif source == "wazuh":
                return await self._normalize_wazuh(raw_log)
            elif source == "endpoint":
                return await self._normalize_endpoint(raw_log)
            else:
                logger.warning(f"Fuente no soportada: {source}")
                return None
        except Exception as e:
            logger.debug(f"Error normalizando log {source}: {e} | Raw: {raw_log}", extra={"raw_log": raw_log})
            return None

    async def _normalize_dns(self, raw: dict) -> Optional[Evento]:
        ts = self._parse_timestamp(raw.get("timestamp"))
        client_ip = raw.get("client", "")
        domain = raw.get("domain", "")
        status = raw.get("status", "")
        
        if not client_ip or not domain:
            return None
            
        hostname = await self._resolver_hostname(client_ip)
        usuario = await self._resolver_usuario(client_ip)
        area = await self._resolver_area(client_ip)
        
        tipo_accion = "block" if status.upper() in ["BLOCKED", "NXDOMAIN"] else "query"

        return Evento(
            timestamp=ts,
            source="dns",
            tipo=tipo_accion,
            interno=EventoInterno(
                ip=client_ip,
                hostname=hostname,
                usuario=usuario,
                area=area
            ),
            externo=EventoExterno(
                valor=domain,
                tipo="dominio"
            )
        )

    async def _normalize_proxy(self, raw: dict) -> Optional[Evento]:
        ts = self._parse_timestamp(raw.get("timestamp"))
        client_ip = raw.get("client_ip", "")
        url = raw.get("url", "")
        
        if not client_ip or not url:
            return None
            
        hostname = await self._resolver_hostname(client_ip)
        usuario = await self._resolver_usuario(client_ip)
        area = await self._resolver_area(client_ip)
        
        # Extraer dominio de la URL para el externo
        domain = url.split("://")[-1].split("/")[0] if "://" in url else url

        return Evento(
            timestamp=ts,
            source="proxy",
            tipo="request",
            interno=EventoInterno(
                ip=client_ip,
                hostname=hostname,
                usuario=usuario,
                area=area
            ),
            externo=EventoExterno(
                valor=domain,
                tipo="dominio"
            )
        )

    async def _normalize_firewall(self, raw: dict) -> Optional[Evento]:
        ts = self._parse_timestamp(raw.get("timestamp"))
        src_ip = raw.get("src_ip", "")
        dst_ip = raw.get("dst_ip", "")
        action = str(raw.get("action", "")).upper()
        
        if not src_ip or not dst_ip:
            return None
            
        src_is_private = self._is_private_ip(src_ip)
        dst_is_private = self._is_private_ip(dst_ip)
        
        # Determinar dirección (interno vs externo)
        if src_is_private and not dst_is_private:
            client_ip = src_ip
            externo_ip = dst_ip
        elif dst_is_private and not src_is_private:
            client_ip = dst_ip
            externo_ip = src_ip
        else:
            # Si ambos son públicos o privados, asumimos source como interno
            client_ip = src_ip
            externo_ip = dst_ip

        hostname = await self._resolver_hostname(client_ip)
        usuario = await self._resolver_usuario(client_ip)
        area = await self._resolver_area(client_ip)
        
        tipo_accion = "block" if action != "ALLOW" else "request"

        return Evento(
            timestamp=ts,
            source="firewall",
            tipo=tipo_accion,
            interno=EventoInterno(
                ip=client_ip,
                hostname=hostname,
                usuario=usuario,
                area=area
            ),
            externo=EventoExterno(
                valor=externo_ip,
                tipo="ip"
            )
        )

    async def _normalize_wazuh(self, raw: dict) -> Optional[Evento]:
        ts = self._parse_timestamp(raw.get("timestamp"))
        
        agent = raw.get("agent", {})
        rule = raw.get("rule", {})
        
        client_ip = agent.get("ip", "")
        hostname = agent.get("name", "unknown")
        descripcion = rule.get("description", "")
        
        if not client_ip:
            return None
            
        usuario = await self._resolver_usuario(client_ip)
        area = await self._resolver_area(client_ip)

        return Evento(
            timestamp=ts,
            source="wazuh",
            tipo="alert",
            interno=EventoInterno(
                ip=client_ip,
                hostname=hostname,
                usuario=usuario,
                area=area
            ),
            externo=EventoExterno(
                valor=descripcion[:255], # Límite por Pydantic/diseño
                tipo="dominio" # Semántico según requerimientos
            )
        )

    async def _normalize_endpoint(self, raw: dict) -> Optional[Evento]:
        ts = self._parse_timestamp(raw.get("timestamp"))
        client_ip = raw.get("host_ip", "")
        hostname = raw.get("hostname", "unknown")
        usuario = raw.get("username", "unknown")
        process_name = raw.get("process_name", "unknown")
        
        if not client_ip:
            return None
            
        area = await self._resolver_area(client_ip)

        return Evento(
            timestamp=ts,
            source="endpoint",
            tipo="process",
            interno=EventoInterno(
                ip=client_ip,
                hostname=hostname,
                usuario=usuario,
                area=area
            ),
            externo=EventoExterno(
                valor=process_name[:255] if process_name else "unknown",
                tipo="hash" # Semántico local
            )
        )
