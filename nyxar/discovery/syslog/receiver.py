"""
Receptor syslog UDP/TCP hacia Redis Stream events:raw (D04).
El firewall envia a NYXAR; no se abre conexion saliente al firewall.
"""

from __future__ import annotations

import asyncio
import logging
import os
import ssl
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Optional

from nyxar.discovery.syslog.detector import SyslogFormatDetector
from nyxar.discovery.syslog.parsers import (
    CefParser,
    FortinetParser,
    JsonFirewallParser,
    LeefParser,
    PfSenseParser,
    Rfc3164Parser,
    Rfc5424Parser,
)

if TYPE_CHECKING:
    from shared.redis_bus import RedisBus

    from nyxar.discovery.engine import InfrastructureMap

logger = logging.getLogger("nyxar.discovery.syslog.receiver")


def _udp_port() -> int:
    try:
        return int(os.environ.get("NYXAR_SYSLOG_UDP_PORT", "514") or "514")
    except ValueError:
        return 514


def _tcp_port() -> int:
    try:
        return int(os.environ.get("NYXAR_SYSLOG_TCP_PORT", "6514") or "6514")
    except ValueError:
        return 6514


def _bind_host() -> str:
    return (os.environ.get("NYXAR_SYSLOG_BIND", "0.0.0.0") or "0.0.0.0").strip()


class SyslogReceiver:
    """
    Escucha syslog (UDP por defecto 514, TCP por defecto 6514).
    Auto-detecta formato en los primeros mensajes y publica Evento en events:raw.
    """

    def __init__(self, redis_bus: "RedisBus", infra: "InfrastructureMap") -> None:
        self.redis_bus = redis_bus
        self.infra = infra
        self.format_detector = SyslogFormatDetector()
        self.parsers: dict[str, Any] = {
            "cef": CefParser(),
            "leef": LeefParser(),
            "rfc5424": Rfc5424Parser(),
            "rfc3164": Rfc3164Parser(),
            "json": JsonFirewallParser(),
            "fortinet": FortinetParser(),
            "pfsense": PfSenseParser(),
        }
        self._detected_format: Optional[str] = None
        self._messages_received = 0

    async def start(self) -> None:
        udp_task = asyncio.create_task(self._start_udp_listener(), name="syslog-udp")
        tcp_task = asyncio.create_task(self._start_tcp_listener(), name="syslog-tcp")
        await asyncio.gather(udp_task, tcp_task)

    async def _start_udp_listener(self) -> None:
        loop = asyncio.get_running_loop()
        transport, _ = await loop.create_datagram_endpoint(
            lambda: _SyslogUDPProtocol(self),
            local_addr=(_bind_host(), _udp_port()),
        )
        logger.info(
            "NYXAR syslog UDP activo en %s:%s",
            _bind_host(),
            _udp_port(),
        )
        try:
            await asyncio.Event().wait()
        finally:
            transport.close()

    async def _start_tcp_listener(self) -> None:
        ssl_ctx = _load_syslog_tls_context()
        server = await asyncio.start_server(
            self._handle_tcp_client,
            host=_bind_host(),
            port=_tcp_port(),
            ssl=ssl_ctx,
        )
        proto = "TLS" if ssl_ctx else "TCP"
        logger.info(
            "NYXAR syslog %s activo en %s:%s",
            proto,
            _bind_host(),
            _tcp_port(),
        )
        async with server:
            await server.serve_forever()

    async def _handle_tcp_client(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        peer = writer.get_extra_info("peername")
        source_ip = peer[0] if peer else ""
        buf = b""
        try:
            while True:
                chunk = await reader.read(8192)
                if not chunk:
                    break
                buf += chunk
                while b"\n" in buf:
                    line, buf = buf.split(b"\n", 1)
                    text = line.decode("utf-8", errors="replace").strip()
                    if text:
                        await self._process_message(text, source_ip)
        finally:
            writer.close()
            try:
                await writer.wait_closed()
            except OSError:
                pass

    async def _process_message(self, raw: str, source_ip: str) -> None:
        self._messages_received += 1
        n = self._messages_received

        if n <= 100:
            detected = self.format_detector.detect(raw)
            if detected and detected != self._detected_format:
                self._detected_format = detected
                self.infra.syslog_format = detected
                logger.info(
                    "Formato syslog detectado: %s (origen %s)",
                    detected,
                    source_ip,
                )

        fmt = self._detected_format
        if not fmt and self.infra.syslog_format:
            fmt = self.infra.syslog_format
        fmt = fmt or "rfc3164"

        parser = self.parsers.get(fmt)
        if not parser:
            parser = self.parsers["rfc3164"]

        parsed = parser.parse(raw, source_ip)
        if not parsed:
            return

        try:
            from api.validators import validate_domain, validate_ip

            evento = _to_evento(parsed, source_ip, validate_ip, validate_domain)
            await self.redis_bus.publish_event(
                self.redis_bus.STREAM_RAW,
                evento.to_redis_dict(),
            )
        except Exception as e:
            logger.warning("syslog publicacion omitida: %s", e)


def _load_syslog_tls_context() -> Optional[ssl.SSLContext]:
    cert = (os.environ.get("NYXAR_SYSLOG_TLS_CERTFILE") or "").strip()
    key = (os.environ.get("NYXAR_SYSLOG_TLS_KEYFILE") or "").strip()
    if not cert or not key:
        return None
    ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    ctx.load_cert_chain(certfile=cert, keyfile=key)
    return ctx


def _to_evento(
    parsed: dict[str, Any],
    source_ip: str,
    validate_ip,
    validate_domain,
):
    from api.models import Evento, EventoExterno, EventoInterno

    sip = (parsed.get("src_ip") or source_ip or "").strip()
    try:
        ip_in = validate_ip(sip)
    except ValueError:
        try:
            ip_in = validate_ip(source_ip) if source_ip else "0.0.0.0"
        except ValueError:
            ip_in = "0.0.0.0"

    dst_ip = (parsed.get("dst_ip") or "").strip()
    dst_host = (parsed.get("dst_host") or "").strip()
    externo: EventoExterno
    if dst_ip:
        try:
            externo = EventoExterno(tipo="ip", valor=validate_ip(dst_ip))
        except ValueError:
            externo = (
                EventoExterno(tipo="dominio", valor=validate_domain(dst_host))
                if dst_host
                else EventoExterno(tipo="texto", valor=dst_ip[:512])
            )
    elif dst_host:
        try:
            externo = EventoExterno(tipo="dominio", valor=validate_domain(dst_host))
        except ValueError:
            externo = EventoExterno(tipo="texto", valor=dst_host[:512])
    else:
        msg = (parsed.get("message") or parsed.get("event_name") or "").strip()
        externo = EventoExterno(
            tipo="texto",
            valor=(msg[:512] if msg else "unknown"),
        )

    act = (parsed.get("action") or "").upper()
    if act in ("DENY", "BLOCK", "DROP", "DROPPED", "BLOCKED"):
        tipo_ev = "block"
    else:
        tipo_ev = "request"

    ts = parsed.get("timestamp")
    ts_dt = _event_timestamp(ts)

    host_l = (
        parsed.get("src_host")
        or parsed.get("hostname")
        or parsed.get("vendor")
        or "desconocido"
    )
    host_s = str(host_l)[:256] if host_l else "desconocido"

    return Evento(
        timestamp=ts_dt,
        source="firewall",
        tipo=tipo_ev,
        interno=EventoInterno(
            ip=ip_in,
            hostname=host_s,
            usuario="desconocido",
            area="desconocido",
        ),
        externo=externo,
        enrichment=None,
        risk_score=None,
        correlaciones=[],
    )


def _event_timestamp(ts: Any) -> datetime:
    if isinstance(ts, datetime):
        if ts.tzinfo is None:
            return ts.replace(tzinfo=timezone.utc)
        return ts.astimezone(timezone.utc)
    if isinstance(ts, (int, float)):
        return datetime.fromtimestamp(float(ts), tz=timezone.utc)
    if isinstance(ts, str) and ts.strip():
        try:
            return datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except ValueError:
            pass
    return datetime.now(timezone.utc)


class _SyslogUDPProtocol(asyncio.DatagramProtocol):
    def __init__(self, receiver: SyslogReceiver) -> None:
        self._receiver = receiver

    def datagram_received(self, data: bytes, addr: tuple[Any, ...]) -> None:
        text = data.decode("utf-8", errors="replace").strip()
        if not text:
            return
        source_ip = str(addr[0]) if addr else ""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return
        loop.create_task(self._receiver._process_message(text, source_ip))
