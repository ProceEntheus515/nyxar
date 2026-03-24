"""
Utilidades de red compartidas entre probes (gateway por defecto).
"""

from __future__ import annotations

import re
import struct
import subprocess
import sys
from typing import Optional


def get_default_gateway_sync() -> Optional[str]:
    if sys.platform.startswith("win"):
        return _gateway_windows()
    return _gateway_linux_proc()


def _gateway_linux_proc() -> Optional[str]:
    try:
        with open("/proc/net/route", encoding="utf-8", errors="replace") as f:
            f.readline()
            for line in f:
                parts = line.split()
                if len(parts) < 3:
                    continue
                dest, gw_hex = parts[1], parts[2]
                if dest == "00000000" and gw_hex != "00000000":
                    try:
                        g = int(gw_hex, 16)
                        return socket_ntoa_le(g)
                    except ValueError:
                        continue
    except OSError:
        pass
    return None


def socket_ntoa_le(addr: int) -> str:
    packed = struct.pack("<I", addr & 0xFFFFFFFF)
    return ".".join(str(b) for b in packed)


def _gateway_windows() -> Optional[str]:
    try:
        out = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                "(Get-NetRoute -DestinationPrefix '0.0.0.0/0' -ErrorAction SilentlyContinue | "
                "Sort-Object RouteMetric | Select-Object -First 1 -ExpandProperty NextHop)",
            ],
            capture_output=True,
            text=True,
            timeout=8,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
            if sys.platform == "win32"
            else 0,
        )
        hop = (out.stdout or "").strip()
        if hop and re.match(r"^\d{1,3}(\.\d{1,3}){3}$", hop):
            return hop
    except (OSError, subprocess.TimeoutExpired, ValueError):
        pass
    return None
