"""Parsers syslog / firewall (CEF, LEEF, RFC, JSON, Fortinet, pfSense)."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any, Optional

_CEF_EXT = re.compile(r"(\b[\w.]+)=((?:\\.|[^\\=\s])*)(?=\s[\w.]+=|\s*$)")


class CefParser:
    def parse(self, raw: str, source_ip: str) -> Optional[dict[str, Any]]:
        try:
            idx = raw.find("CEF:")
            if idx < 0:
                return None
            cef_part = raw[idx:]
            parts = cef_part.split("|", 7)
            if len(parts) < 7:
                return None
            extensions: dict[str, str] = {}
            if len(parts) >= 8 and parts[7]:
                for m in _CEF_EXT.finditer(parts[7]):
                    extensions[m.group(1)] = m.group(2).replace("\\=", "=").replace("\\|", "|")
            rt = extensions.get("rt") or extensions.get("end")
            ts = _coerce_ts(rt)
            return {
                "vendor": parts[1],
                "product": parts[2],
                "event_name": parts[5] if len(parts) > 5 else "",
                "severity": parts[6] if len(parts) > 6 else "",
                "src_ip": extensions.get("src") or extensions.get("saddr") or source_ip,
                "dst_ip": extensions.get("dst") or extensions.get("daddr", ""),
                "dst_host": extensions.get("dhost", ""),
                "src_host": extensions.get("shost", ""),
                "dst_port": extensions.get("dpt", ""),
                "action": extensions.get("act") or extensions.get("outcome", ""),
                "protocol": extensions.get("proto", ""),
                "timestamp": ts,
            }
        except (IndexError, ValueError):
            return None


class LeefParser:
    def parse(self, raw: str, source_ip: str) -> Optional[dict[str, Any]]:
        try:
            idx = raw.find("LEEF:")
            if idx < 0:
                return None
            rest = raw[idx + 5 :]
            segs = rest.split("|", 5)
            if len(segs) < 5:
                return None
            attrs = segs[-1] if len(segs) > 5 else ""
            fields: dict[str, str] = {}
            for part in re.split(r"\t+", attrs):
                if "=" in part:
                    k, _, v = part.partition("=")
                    fields[k.strip()] = v.strip()
            return {
                "vendor": segs[1] if len(segs) > 1 else "",
                "product": segs[2] if len(segs) > 2 else "",
                "src_ip": fields.get("src") or fields.get("srcIp") or source_ip,
                "dst_ip": fields.get("dst") or fields.get("dstIp", ""),
                "action": fields.get("cat") or fields.get("devAction", ""),
                "protocol": fields.get("proto", ""),
                "timestamp": datetime.now(timezone.utc),
            }
        except (IndexError, ValueError):
            return None


class Rfc5424Parser:
    _HDR = re.compile(
        r"^<(?P<priv>\d+)>(?P<ver>\d)\s+"
        r"(?P<ts>\S+)\s+(?P<host>\S+)\s+(?P<app>\S+)\s+"
        r"(?P<proc>\S+)\s+(?P<msgid>\S+)\s+"
        r"(?P<sd>(?:\[.+?\]|-))\s*(?P<msg>.*)$"
    )

    def parse(self, raw: str, source_ip: str) -> Optional[dict[str, Any]]:
        m = self._HDR.match(raw.strip())
        if not m:
            return None
        ts = _parse_rfc5424_ts(m.group("ts"))
        return {
            "src_ip": source_ip,
            "dst_ip": "",
            "dst_host": m.group("host"),
            "action": "",
            "protocol": "",
            "timestamp": ts,
            "message": m.group("msg") or "",
        }


class Rfc3164Parser:
    def parse(self, raw: str, source_ip: str) -> Optional[dict[str, Any]]:
        s = raw.strip()
        m = re.match(r"^<\d+>(.+)$", s, re.DOTALL)
        body = m.group(1) if m else s
        return {
            "src_ip": source_ip,
            "dst_ip": "",
            "action": "",
            "protocol": "",
            "timestamp": datetime.now(timezone.utc),
            "message": body[:2048],
        }


class JsonFirewallParser:
    def parse(self, raw: str, source_ip: str) -> Optional[dict[str, Any]]:
        payload = raw.strip()
        brace = payload.find("{")
        if brace >= 0:
            payload = payload[brace:]
        elif ">" in payload[:64]:
            payload = payload.split(">", 1)[-1].strip()
        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            return None
        if not isinstance(data, dict):
            return None
        return {
            "src_ip": str(
                data.get("src")
                or data.get("src_ip")
                or data.get("source_ip")
                or source_ip
            ),
            "dst_ip": str(data.get("dst") or data.get("dst_ip") or data.get("dest_ip", "")),
            "dst_host": str(data.get("dst_host") or data.get("destination", "")),
            "action": str(data.get("action") or data.get("result", "")),
            "protocol": str(data.get("protocol") or data.get("proto", "")),
            "timestamp": data.get("timestamp") or data.get("time"),
        }


class FortinetParser:
    _KV = re.compile(r'(\w+)="([^"]*)"|(\w+)=(\S+)')

    def parse(self, raw: str, source_ip: str) -> Optional[dict[str, Any]]:
        fields: dict[str, str] = {}
        for m in self._KV.finditer(raw):
            if m.group(1):
                fields[m.group(1)] = m.group(2)
            else:
                fields[m.group(3)] = m.group(4)
        if not fields or not any(
            k in fields for k in ("date", "devname", "type", "srcip")
        ):
            return None
        date_s = fields.get("date", "")
        time_s = fields.get("time", "")
        ts = datetime.now(timezone.utc)
        if date_s and time_s:
            try:
                ts = datetime.fromisoformat(f"{date_s}T{time_s}").replace(
                    tzinfo=timezone.utc
                )
            except ValueError:
                pass
        return {
            "src_ip": fields.get("srcip") or source_ip,
            "dst_ip": fields.get("dstip", ""),
            "dst_port": fields.get("dstport", ""),
            "action": (fields.get("action") or "").upper(),
            "protocol": fields.get("proto", ""),
            "timestamp": ts,
            "policy": fields.get("policyname", ""),
            "interface": fields.get("srcintf", ""),
            "vendor": "fortinet",
            "src_host": fields.get("devname", ""),
        }


class PfSenseParser:
    def parse(self, raw: str, source_ip: str) -> Optional[dict[str, Any]]:
        s = raw.lower()
        if "filterlog" not in s and " pf:" not in s:
            return None
        src_m = re.search(
            r"src[=:]\s*([0-9a-fA-F.:]+)|,([0-9]{1,3}(?:\.[0-9]{1,3}){3}),",
            raw,
        )
        dst_m = re.search(
            r"dst[=:]\s*([0-9a-fA-F.:]+)|,([0-9]{1,3}(?:\.[0-9]{1,3}){3}),",
            raw,
        )
        src = ""
        if src_m:
            src = src_m.group(1) or src_m.group(2) or ""
        dst = ""
        if dst_m:
            dst = dst_m.group(1) or dst_m.group(2) or ""
        act = "BLOCK" if "block" in s else "PASS" if "pass" in s else ""
        return {
            "src_ip": src or source_ip,
            "dst_ip": dst,
            "action": act,
            "protocol": "",
            "timestamp": datetime.now(timezone.utc),
            "vendor": "pfsense",
        }


def _coerce_ts(rt: Optional[str]) -> datetime:
    if not rt:
        return datetime.now(timezone.utc)
    try:
        ms = int(rt)
        if ms > 1_000_000_000_000:
            ms //= 1000
        return datetime.fromtimestamp(ms / 1000.0, tz=timezone.utc)
    except (ValueError, TypeError, OSError):
        pass
    try:
        return datetime.fromisoformat(rt.replace("Z", "+00:00"))
    except ValueError:
        return datetime.now(timezone.utc)


def _parse_rfc5424_ts(ts: str) -> datetime:
    if not ts or ts == "-":
        return datetime.now(timezone.utc)
    if ts.endswith("Z"):
        ts = ts[:-1] + "+00:00"
    for fmt in (
        None,
        "%Y-%m-%dT%H:%M:%S.%f%z",
        "%Y-%m-%dT%H:%M:%S%z",
    ):
        try:
            if fmt is None:
                return datetime.fromisoformat(ts)
            return datetime.strptime(ts, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return datetime.now(timezone.utc)
