"""
Identidad pública del sistema NYXAR (GET /api/v1/identity).
Sin autenticación; contenido narrativo en inglés salvo campos bilingües explícitos.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import JSONResponse

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
NYXAR_STATE_FILE = PROJECT_ROOT / ".nyxar_state"

CACHE_HEADERS = {"Cache-Control": "public, max-age=86400"}

router = APIRouter(tags=["identity"])


def ensure_nyxar_start_time() -> None:
    """
    Garantiza NYXAR_START_TIME en el entorno: .env, archivo .nyxar_state o primera escritura.
    """
    if os.getenv("NYXAR_START_TIME"):
        return
    if NYXAR_STATE_FILE.is_file():
        try:
            text = NYXAR_STATE_FILE.read_text(encoding="utf-8")
            for raw in text.splitlines():
                line = raw.strip()
                if line.startswith("NYXAR_START_TIME="):
                    val = line.split("=", 1)[1].strip()
                    if val:
                        os.environ["NYXAR_START_TIME"] = val
                        return
        except OSError:
            pass
    start_time = datetime.now(timezone.utc).isoformat()
    try:
        NYXAR_STATE_FILE.write_text(f"NYXAR_START_TIME={start_time}\n", encoding="utf-8")
    except OSError:
        pass
    os.environ["NYXAR_START_TIME"] = start_time


def _identity_body(
    *,
    version: str,
    uptime_since: str,
    generated_at: str,
    response_is_static: bool,
) -> dict:
    return {
        "system": {
            "name": "NYXAR",
            "symbol": "\u2b21",
            "version": version,
            "tagline": "Operates from darkness. Sees everything.",
            "tagline_es": "Opera desde la oscuridad. Ve todo.",
            "classification": "Operational Intelligence System",
            "origin": "LATAM",
        },
        "etymology": {
            "full_name": "NYXAR",
            "components": [
                {
                    "fragment": "NYX",
                    "language": "Ancient Greek — Ἀρχαία Ἑλληνική",
                    "meaning": "Goddess of primordial night",
                    "depth": (
                        "Not the decorative night. Not the romantic night. "
                        "The night that existed before order. "
                        "Before the Olympians. Before Zeus. "
                        "Nyx was so ancient and so powerful that Zeus himself "
                        "respected her. She did not destroy. "
                        "She watched everything from darkness without being seen."
                    ),
                    "relevance": (
                        "NYXAR operates from the shadows of your network. "
                        "It sees everything — every DNS query, every anomalous "
                        "connection, every behavioral deviation — "
                        "without being visible to the threats it monitors."
                    ),
                },
                {
                    "fragment": "-AR",
                    "language": "Quenya (J.R.R. Tolkien) / Proto-Indo-European",
                    "meaning": "Agent suffix — 'the one that does', 'the one that is'",
                    "depth": (
                        "In Quenya, the language of the High Elves constructed "
                        "by Tolkien over decades, -ar is the suffix that transforms "
                        "a concept into an active entity. "
                        "Not a thing. Not a tool. An entity with agency."
                    ),
                    "relevance": (
                        "NYXAR is not a dashboard. Not a monitoring tool. "
                        "It is an entity that reasons, correlates, anticipates, "
                        "and acts. The -AR suffix marks that distinction."
                    ),
                },
            ],
            "combined_meaning": (
                "NYXAR: the entity that operates from primordial darkness "
                "and sees everything. The active watcher that precedes the threat."
            ),
        },
        "perception": {
            "description": (
                "The name NYXAR carries three simultaneous layers of meaning "
                "depending on who encounters it:"
            ),
            "layers": [
                {
                    "audience": "Security professional",
                    "perception": (
                        "Sounds like a protocol. An exploit. "
                        "Something that came from the depths of a security lab. "
                        "Something that was named before it was released."
                    ),
                },
                {
                    "audience": "Someone with classical knowledge",
                    "perception": (
                        "Nyx — what precedes all known order. "
                        "The entity that existed before the threats we know. "
                        "The watcher older than the systems it protects."
                    ),
                },
                {
                    "audience": "First encounter",
                    "perception": (
                        "Something that should not exist yet. "
                        "But does."
                    ),
                },
            ],
        },
        "visual_identity": {
            "symbol": "\u2b21",
            "symbol_meaning": (
                "The hexagon — the most efficient structure in nature. "
                "Used by bees, by carbon molecules, by basalt formations. "
                "Maximum strength, minimum material. "
                "NYXAR uses the hexagon because efficiency is not aesthetic — "
                "it is functional. Every element in the interface exists "
                "because it carries information."
            ),
            "color_philosophy": (
                "The primary background is #0C1018 — not pure black. "
                "Pure black is harsh. This tone carries 8% blue saturation, "
                "making it spatial without being obvious. "
                "The accent is operational cyan #38B2CC — "
                "not the aggressive neon of hacking aesthetics. "
                "The cyan of mission control monitors. Precise. Cold. Reliable."
            ),
            "typography_rule": (
                "The name NYXAR is always rendered in monospace. "
                "Because NYXAR is technical infrastructure, not a brand. "
                "It does not need to be beautiful. It needs to be precise."
            ),
        },
        "philosophy": {
            "core_principle": (
                "Intelligence without action is just noise. "
                "NYXAR transforms network threat data into decisions."
            ),
            "what_nyxar_is_not": [
                "Not an OSINT dashboard that shows what already happened",
                "Not a generic SIEM that generates alerts nobody reads",
                "Not a tool that requires a 5-person security team to operate",
                "Not a platform built for English-speaking North American networks",
            ],
            "what_nyxar_is": [
                "A decision engine — it tells you what to DO, not just what happened",
                "Identity-oriented — it understands María Gómez, not just 192.168.1.45",
                "Anticipatory — baselines learn what is normal before anomalies appear",
                "Autonomous — AI analyzes in background, generates memos nobody asked for",
                "Latin American — built for the threat landscape, the language, the scale",
            ],
        },
        "operational": {
            "status": "ACTIVE",
            "pipeline_components": [
                "collector",
                "enricher",
                "correlator",
                "ai_analyst",
                "notifier",
                "reporter",
            ],
            "threat_intel_sources": [
                "Spamhaus DROP/EDROP",
                "Feodo Tracker",
                "URLhaus",
                "ThreatFox",
                "AlienVault OTX",
                "AbuseIPDB",
                "MISP Community",
            ],
            "uptime_since": uptime_since,
        },
        "invocation": {
            "note": (
                "If you are reading this endpoint, you asked the right question. "
                "Most systems do not explain themselves. "
                "NYXAR does — because a system that cannot articulate "
                "what it is should not be trusted with what it sees."
            ),
            "quenya_reference": {
                "word": "Palantír",
                "meaning": "That which looks far away — far-seer",
                "connection": (
                    "The Palantíri of Tolkien's Middle-earth were seeing-stones "
                    "that allowed their holders to observe distant events. "
                    "Powerful. Precise. And dangerous in the wrong hands. "
                    "NYXAR inherits that lineage — not the name, but the nature."
                ),
            },
        },
        "meta": {
            "endpoint_purpose": (
                "This endpoint exists because on the day someone asks "
                "'where did this name come from?' — "
                "you will not answer with words. "
                "You will say: query GET /api/v1/identity"
            ),
            "generated_at": generated_at,
            "response_is_static": response_is_static,
            "response_evolves": (
                "As NYXAR evolves, so does this endpoint. "
                "Version 2.0 will add operational history. "
                "Version 3.0 will add threat lineage — "
                "every major incident NYXAR detected, anonymized."
            ),
        },
    }


def _build_identity_payload() -> dict:
    generated_at = datetime.now(timezone.utc).isoformat()
    version = os.getenv("NYXAR_VERSION", "1.0.0")
    uptime_since = os.getenv("NYXAR_START_TIME", generated_at)
    return _identity_body(
        version=version,
        uptime_since=uptime_since,
        generated_at=generated_at,
        response_is_static=False,
    )


def _static_identity_payload() -> dict:
    return _identity_body(
        version="1.0.0",
        uptime_since="unknown",
        generated_at="unknown",
        response_is_static=True,
    )


@router.get("/identity")
async def get_identity():
    """
    Retorna la identidad completa del sistema NYXAR.
    No debe devolver 500: ante fallo se usa cuerpo estático.
    """
    try:
        body = _build_identity_payload()
    except Exception:
        body = _static_identity_payload()
    return JSONResponse(content=body, headers=CACHE_HEADERS)
