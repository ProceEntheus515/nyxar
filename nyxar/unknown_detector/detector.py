"""
Unknown Detector: Claude sobre muestra cruda sin hipótesis previas (V8 U08).
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

try:
    import anthropic
except ImportError:
    anthropic = None  # type: ignore

try:
    from motor.motor_asyncio import AsyncIOMotorDatabase
except ImportError:
    AsyncIOMotorDatabase = Any  # type: ignore

from nyxar.unknown_detector.sampler import StreamSampler

try:
    from shared.logger import get_logger

    logger = get_logger("unknown_detector.detector")
except ImportError:
    logger = logging.getLogger("nyxar.unknown_detector.detector")

_PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class UnknownDetector:
    """
    Detector de patrones sin nombre: stream crudo y pregunta abierta.
    """

    RUN_INTERVAL_HOURS = 6
    MAX_FINDINGS_PER_RUN = 5
    DEFAULT_MODEL = "claude-sonnet-4-20250514"

    def __init__(
        self,
        db: AsyncIOMotorDatabase,
        redis_bus: Optional[Any] = None,
    ) -> None:
        self.db = db
        self.redis = redis_bus
        self.sampler = StreamSampler()
        api_key = os.getenv("ANTHROPIC_API_KEY", "")
        self._client: Any = None
        if anthropic and api_key:
            self._client = anthropic.AsyncAnthropic(api_key=api_key)
        self._model = os.getenv("ANTHROPIC_UNKNOWN_MODEL", self.DEFAULT_MODEL)

    async def start(self) -> None:
        """Bucle periódico (p. ej. worker dedicado)."""
        while True:
            try:
                await self.run_detection_session()
            except Exception as e:
                logger.error("Unknown Detector error: %s", e)
            await asyncio.sleep(self.RUN_INTERVAL_HOURS * 3600)

    async def run_detection_session(self) -> list[dict[str, Any]]:
        if self._client is None:
            logger.warning(
                "Unknown Detector: ANTHROPIC_API_KEY no configurada, sesión omitida"
            )
            return []

        logger.info("Unknown Detector: iniciando sesión de exploración")

        sample = await self.sampler.sample(self.db, hours_back=6)
        if len(sample) < 20:
            logger.info("Muestra insuficiente, omitiendo sesión")
            return []

        context = self._build_raw_context(sample)
        prompt_path = _PROMPTS_DIR / "raw_scan.txt"
        prompt_template = prompt_path.read_text(encoding="utf-8")

        try:
            response = await self._client.messages.create(
                model=self._model,
                max_tokens=2000,
                system=prompt_template,
                messages=[{"role": "user", "content": context}],
            )
            raw_response = response.content[0].text
            findings = self._parse_findings(raw_response)
        except Exception as e:
            logger.error("Claude API error en Unknown Detector: %s", e)
            return []

        for finding in findings[: self.MAX_FINDINGS_PER_RUN]:
            await self._persist_finding(finding, sample)
            if self.redis is not None:
                try:
                    await self.redis.publish_alert(
                        "dashboard:alerts",
                        {"tipo": "unknown_finding", "data": finding},
                    )
                except Exception as ex:
                    logger.warning("publish_alert unknown_finding: %s", ex)

        logger.info("Unknown Detector: %s hallazgos en esta sesión", len(findings))
        return findings

    def _build_raw_context(self, sample: list[dict[str, Any]]) -> str:
        lines = [
            f"MUESTRA DE {len(sample)} EVENTOS — ÚLTIMAS 6 HORAS",
            f"Timestamp de análisis: {_utcnow().isoformat()}",
            "",
            "ts_hora | usuario | area | tipo | valor_externo | reputacion | score",
            "─" * 80,
        ]

        for ev in sample:
            ts = ev.get("timestamp")
            hora = "??"
            if isinstance(ts, datetime):
                hora = ts.strftime("%H:%M")
            elif isinstance(ts, str) and len(ts) >= 16:
                hora = ts[11:16] if "T" in ts else ts[:5]

            usuario = str(ev.get("usuario") or "?")[:12]
            area = str(ev.get("area") or "?")[:8]
            tipo = str(ev.get("source") or "?")[:5]
            valor = str(ev.get("valor_externo") or "?")[:35]
            rep = str(ev.get("reputacion") or "?")[:10]
            score = ev.get("risk_score") or 0

            lines.append(
                f"{hora} | {usuario:<12} | {area:<8} | {tipo:<5} | "
                f"{valor:<35} | {rep:<10} | {score}"
            )

        return "\n".join(lines)

    def _parse_findings(self, raw: str) -> list[dict[str, Any]]:
        try:
            clean = raw.strip()
            if clean.startswith("```"):
                parts = clean.split("```")
                clean = parts[1] if len(parts) > 1 else clean
                if clean.startswith("json"):
                    clean = clean[4:].lstrip()

            data = json.loads(clean)
            if isinstance(data, list):
                return [x for x in data if isinstance(x, dict)]
            if isinstance(data, dict) and "findings" in data:
                inner = data["findings"]
                return [x for x in inner if isinstance(x, dict)] if isinstance(inner, list) else []
            return []
        except Exception:
            return []

    async def _persist_finding(
        self,
        finding: dict[str, Any],
        sample: list[dict[str, Any]],
    ) -> None:
        doc: dict[str, Any] = {
            "id": f"uf_{uuid.uuid4().hex[:16]}",
            "timestamp": _utcnow(),
            "tipo": "unknown_finding",
            "finding": finding,
            "sample_size": len(sample),
            "estado": "nuevo",
            "confirmado": False,
            "es_falso_positivo": False,
        }
        await self.db.unknown_findings.insert_one(doc)
