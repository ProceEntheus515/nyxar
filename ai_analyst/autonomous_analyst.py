import os
import json
import uuid
import asyncio
from datetime import datetime, timezone, timedelta
import anthropic

from shared.logger import get_logger
from shared.mongo_client import MongoClient
from shared.redis_bus import RedisBus
from shared.heartbeat import heartbeat_loop
from prompt_defense import (
    CLAUDE_PROMPT_INJECTION_SYSTEM_PREFIX,
    PromptInjectionDefense,
)

logger = get_logger("ai.autonomous")

class AutonomousAnalyst:
    ANALYSIS_INTERVAL = 900  # cada 15 minutos
    
    def __init__(self):
        self.mongo = MongoClient()
        self.redis_bus = RedisBus()
        self.api_key = os.getenv("ANTHROPIC_API_KEY", "")
        self.model = "claude-sonnet-4-20250514"
        self._running = False
        
        prompt_path = os.path.join(os.path.dirname(__file__), "prompts", "autonomous.txt")
        try:
            with open(prompt_path, "r", encoding="utf-8") as f:
                self.prompt_template = f.read()
        except OSError:
            self.prompt_template = "Contexto: {context}.\nReglas: Respondé JSON."
        self._prompt_defense = PromptInjectionDefense()

    async def run(self) -> None:
        """Loop infinito que corre el análisis cada ANALYSIS_INTERVAL segundos"""
        self._running = True
        await self.mongo.connect()
        await self.redis_bus.connect()
        asyncio.create_task(heartbeat_loop(self.redis_bus, "ai_analyst"), name="ai_analyst-hb")
        logger.info(f"iniciando AutonomousAnalyst. Intervalo: {self.ANALYSIS_INTERVAL}s")
        await asyncio.sleep(60) # Demora en arrancar para permitir que haya data viva
        while self._running:
            try:
                await self.analyze_current_state()
            except Exception as e:
                logger.error(f"Error en loop autónomo: {e}")
            await asyncio.sleep(self.ANALYSIS_INTERVAL)

    def _build_context_summary(self, eventos, identidades, incidentes, honeypots) -> str:
        """
        Construye un resumen compacto del estado actual para incluir en el prompt.
        Formato diseñado para ser informativo pero no desperdiciar tokens.
        Máximo 2000 tokens de contexto.
        """
        d = self._prompt_defense
        ctx = []
        ctx.append("--- IDENTIDADES DE ALTO RIESGO (>40) ---")
        for i in identidades:
            iid = d.sanitize_plain_text(str(i.get("id") or ""), "identity.id", 120)
            area = d.sanitize_plain_text(str(i.get("area") or ""), "identity.area", 80)
            score = i.get("risk_score", "N/A")
            ctx.append(f"ID: {iid} - Score: {score} - Area: {area}")

        ctx.append("\n--- INCIDENTES ACTIVOS ---")
        for inc in incidentes:
            inc_id = d.sanitize_plain_text(str(inc.get("id") or ""), "incident.id", 120)
            sev = d.sanitize_plain_text(str(inc.get("severidad") or ""), "incident.severidad", 32)
            host = d.sanitize_plain_text(str(inc.get("host_afectado") or ""), "incident.host", 120)
            tech = d.sanitize_plain_text(str(inc.get("mitre_technique") or ""), "incident.mitre", 80)
            ctx.append(
                f"Incidente: {inc_id} - Severidad: {sev} - Afectado: {host} - Técnica: {tech}"
            )

        ctx.append("\n--- HONEYPOT HITS (24H) ---")
        ctx.append(f"Total Honeypot Hits detectados intrusión: {honeypots}")

        filtrados = [
            e
            for e in eventos[:200]
            if e.get("enrichment", {}).get("risk_score", 0) > 30
        ][:50]
        ctx.append("\n--- MUESTRA DE ACTIVIDAD RECIENTE (ultimos 15 min, riesgo >30) ---")
        ctx.append(d.build_safe_context(filtrados))

        return "\n".join(ctx)[:8000]

    async def analyze_current_state(self) -> None:
        """
        Recopila contexto, llama a Claude y, si hay memo útil, persiste en MongoDB
        y notifica al dashboard vía Redis PubSub (canal dashboard:events, tipo ai_memo).
        """
        db = self.mongo.db

        identidades = await db.identities.find({"risk_score": {"$gte": 40}}).to_list(50)
        incidentes = await db.incidents.find({"estado": "abierto"}).to_list(50)

        hace_24h = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        hits_hp = await db.honeypot_hits.count_documents({"timestamp": {"$gte": hace_24h}})

        hace_15m = (datetime.now(timezone.utc) - timedelta(minutes=15)).isoformat()
        eventos_raw = await db.events.find({"timestamp": {"$gte": hace_15m}}).to_list(500)

        if not incidentes and not identidades and hits_hp == 0:
            logger.info("AutonomousAnalyst: Red pacífica. Ahorrando tokens. Saltando.")
            return

        context_str = self._build_context_summary(eventos_raw, identidades, incidentes, hits_hp)
        prompt_filled = self.prompt_template.replace("{context}", context_str)

        if not self.api_key:
            logger.warning("Falta API KEY para autonomous.")
            return

        try:
            client = anthropic.AsyncAnthropic(api_key=self.api_key)
            resp = await client.messages.create(
                model=self.model,
                max_tokens=600,
                temperature=0.3,
                system=CLAUDE_PROMPT_INJECTION_SYSTEM_PREFIX,
                messages=[{"role": "user", "content": prompt_filled}],
            )
            raw = resp.content[0].text if resp.content else "{}"

            cl = raw.strip()
            if cl.startswith("```json"):
                cl = cl[7:].strip()
            elif cl.startswith("```"):
                cl = cl[3:].strip()
            if cl.endswith("```"):
                cl = cl[:-3].strip()

            parsed = json.loads(cl)

            if parsed.get("prioridad") == "ninguna":
                logger.info("Claude determinó que la actividad es normal. Omitiendo alerta general.")
                return

            memo_id = f"MEMO-AUTO-{uuid.uuid4().hex[:8]}"
            eventos_relacionados = parsed.get("eventos_relacionados") or parsed.get("eventos_clave") or []

            memo_doc = {
                "id": memo_id,
                "tipo": "autonomo",
                "titulo": (parsed.get("titulo") or "").strip() or "Análisis autónomo",
                "contenido": (parsed.get("contenido") or "").strip(),
                "prioridad": (parsed.get("prioridad") or "media").lower(),
                "eventos_relacionados": list(eventos_relacionados) if isinstance(eventos_relacionados, list) else [],
                "incident_id": "GLOBAL-AUTO",
                "generado_por": self.model,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "accion_inmediata": parsed.get("accion_inmediata"),
            }

            await self.mongo.db.ai_memos.insert_one(memo_doc)

            await self.redis_bus.publish_alert(
                "dashboard:events",
                {"tipo": "ai_memo", "data": memo_doc},
            )

            logger.info("Memo publicado: %s — %s", memo_doc["prioridad"], memo_doc["titulo"])

        except Exception as e:
            logger.error(f"Error analizando con Claude: {e}")
