import os
import json
import uuid
import asyncio
from datetime import datetime, timezone
import anthropic

from shared.logger import get_logger
from shared.mongo_client import MongoClient

logger = get_logger("ai.ceo_translator")

class CeoTranslator:
    def __init__(self):
        self.mongo = MongoClient()
        self.api_key = os.getenv("ANTHROPIC_API_KEY", "")
        # Cargamos el prompt
        prompt_path = os.path.join(os.path.dirname(__file__), "prompts", "ceo_view.txt")
        try:
            with open(prompt_path, "r", encoding="utf-8") as f:
                self.prompt_template = f.read()
        except Exception:
            self.prompt_template = "Estadísticas: {context}. Genera un JSON {'titulo':'x', 'resumen':'y', 'acciones':'z'}."
            logger.warning("No se encontró ceo_view.txt, usando fallback inline")

    async def _gather_context(self) -> str:
        db = self.mongo.db
        
        # 1. Incidentes Críticos / Altos Abiertos
        crit_abiertos = await db.incidents.find({"estado": {"$nin": ["cerrado", "falso_positivo"]}, "severidad": {"$in": ["CRÍTICA", "CRITICA", "ALTA"]}}).to_list(100)
        
        # 2. Risk Scores
        top_risk = await db.identities.find({"risk_score": {"$gt": 40}}).sort("risk_score", -1).limit(5).to_list(5)
        
        # 3. Honeypots < 24h
        ayer = (datetime.now(timezone.utc).timestamp() - 86400)
        hits = await db.honeypot_hits.count_documents({"timestamp": {"$gte": datetime.fromtimestamp(ayer, timezone.utc).isoformat()}})
        
        ctx = []
        ctx.append(f"- Incidentes Críticos/Altos activos: {len(crit_abiertos)}")
        if crit_abiertos:
            cats = [i.get('mitre_technique', 'N/A') for i in crit_abiertos]
            ctx.append(f"- Tipo de técnicas bajo ataque: {', '.join(set(cats))}")
        
        ctx.append(f"- Identidades en Riesgo Alto (>40): {len(top_risk)}")
        ctx.append(f"- Alarmas silenciosas (Honeypots) disparadas en ultimas 24h: {hits}")
        
        return "\n".join(ctx)

    async def generate(self) -> dict:
        """
        1. Recopilar: incidentes abiertos críticos y altos, risk scores actuales, honeypot hits.
        2. Llamar a Claude con prompt de ceo_view.txt
        3. Retornar dict del memo tipo='ceo'
        """
        ctx_str = await self._gather_context()
        prompt_filled = self.prompt_template.replace("{context}", ctx_str)
        
        memo_id = f"MEMO-CEO-{uuid.uuid4().hex[:8]}"
        
        if not self.api_key:
            logger.warning("Generando CEO View simulada (Fallback) por carencia de ANTHROPIC_API_KEY")
            fake_content = {
                "titulo": "Executive Posture - Fallback",
                "resumen": "El sistema se encuentra operando bajo parámetros estándar. Contexto simulado.",
                "acciones": "Adquirir o validar API keys Anthropic."
            }
            return {
                "id": memo_id,
                "incident_id": "GLOBAL",
                "tipo": "ceo",
                "contenido": fake_content["resumen"],
                "detalles": fake_content,
                "generado_por": "claude-sonnet-4-20250514 (Simulado)",
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            
        try:
            client = anthropic.AsyncAnthropic(api_key=self.api_key)
            resp = await client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=600,
                temperature=0.2,
                messages=[{"role": "user", "content": prompt_filled}]
            )
            
            raw_res = resp.content[0].text if resp.content else "{}"
            
            # Limpiar posible basura markdown
            clean_res = raw_res.strip()
            if clean_res.startswith("```json"):
                clean_res = clean_res[7:].strip()
            if clean_res.endswith("```"):
                clean_res = clean_res[:-3].strip()
                
            parsed = json.loads(clean_res)
            
            return {
                "id": memo_id,
                "incident_id": "GLOBAL",
                "tipo": "ceo",
                "contenido": parsed.get("resumen", ""),
                "detalles": parsed,
                "generado_por": "claude-sonnet-4-20250514",
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"CEO View Translator error: {e}")
            return {}
