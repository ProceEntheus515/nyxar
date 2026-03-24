"""Deteccion automatica del formato syslog (D04)."""

from __future__ import annotations

import json
import re
from typing import Optional


class SyslogFormatDetector:
    def detect(self, raw: str) -> Optional[str]:
        if not raw or not raw.strip():
            return None
        s = raw.strip()
        if "CEF:" in s or s.startswith("CEF:"):
            return "cef"
        if "LEEF:" in s or s.startswith("LEEF:"):
            return "leef"
        if s.startswith("{"):
            try:
                json.loads(s)
                return "json"
            except json.JSONDecodeError:
                pass
        payload = s.split(">", 1)[-1] if ">" in s[:48] else s
        if payload.strip().startswith("{"):
            try:
                json.loads(payload.strip())
                return "json"
            except json.JSONDecodeError:
                pass
        ls = s.lower()
        if "date=" in ls and "time=" in ls and "type=" in ls:
            return "fortinet"
        if "filterlog:" in ls or " pf:" in ls or "pfsense" in ls:
            return "pfsense"
        if re.match(r"^<\d+>1\s+", s):
            return "rfc5424"
        return "rfc3164"
