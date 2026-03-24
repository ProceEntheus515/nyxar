import os
import json
import uuid
from datetime import datetime, timezone, timedelta
import asyncio
import anthropic

from shared.logger import get_logger
from shared.mongo_client import MongoClient
from prompt_defense import (
    CLAUDE_PROMPT_INJECTION_SYSTEM_PREFIX,
    PromptInjectionDefense,
)

logger = get_logger("ai.incident_analyzer")

class IncidentAnalyzer:
    def __init__(self):
        self.mongo = MongoClient()
        self.api_key = os.getenv("ANTHROPIC_API_KEY", "")
        self.model = "claude-sonnet-4-20250514"
        
        prompt_path = os.path.join(os.path.dirname(__file__), "prompts", "incident.txt")
        try:
            with open(prompt_path, "r", encoding="utf-8") as f:
                self.prompt_template = f.read()
        except Exception:
            self.prompt_template = "Incident: {incident}\nBaseline: {baseline}\nHistory: {history}\nAnalyze json."
            logger.warning("No se encontró incident.txt, usando fallback")
        self._prompt_defense = PromptInjectionDefense()

    async def analyze(self, incident_id: str) -> dict:
        """
        Analiza un incidente específico bajo demanda.
        """
        db = self.mongo.db
        
        # 1. Cargar el incidente y eventos relacionados
        inc = await db.incidents.find_one({"id": incident_id})
        if not inc:
            logger.error(f"IncidentAnalyzer: Incidente {incident_id} no encontrado")
            return {}
            
        identidad_id = inc.get("host_afectado", "")
        
        # 2. Cargar el baseline de la identidad
        baseline = await db.identities.find_one({"id": identidad_id}) or {}
        
        # 3. Cargar últimos 7 días de eventos
        hace_7_dias = (datetime.now(timezone.utc) - timedelta(days=7)).timestamp() * 1000
        historia_cursor = db.events.find({
            "$or": [
                {"interno.ip": identidad_id},
                {"interno.id_usuario": identidad_id}
            ],
            "timestamp": {"$gte": datetime.fromtimestamp(hace_7_dias / 1000, timezone.utc).isoformat()}
        }).sort("timestamp", -1).limit(100)  # limitamos a 100 para no reventar tokens
        historia_eventos = await historia_cursor.to_list(100)
        
        # Ensamblar strings para contexto (sin datos externos crudos en el prompt)
        d = self._prompt_defense
        inc_san = d.sanitize_document_for_llm(inc, "incident")
        base_san = d.sanitize_document_for_llm(baseline, "baseline")
        inc_str = json.dumps(inc_san, default=str, ensure_ascii=False)
        base_str = json.dumps(base_san, default=str, ensure_ascii=False)
        hist_lines = []
        for idx, e in enumerate(historia_eventos):
            ts = d.sanitize_plain_text(str(e.get("timestamp") or ""), f"hist[{idx}].ts", 48)
            src = d.sanitize_plain_text(str(e.get("source") or ""), f"hist[{idx}].source", 48)
            ext = e.get("externo") or {}
            val = d.sanitize_plain_text(
                str(ext.get("valor") if isinstance(ext, dict) else ""), f"hist[{idx}].valor", 200
            )
            hist_lines.append(f"[{ts}] {src} - {val}")
        hist_str = "\n".join(hist_lines)
        
        prompt_filled = self.prompt_template.format(
            incident=inc_str, 
            baseline=base_str, 
            history=hist_str
        )
        memo_id = f"MEMO-INC-{uuid.uuid4().hex[:8]}"
        
        if not self.api_key:
            return {
                "id": memo_id,
                "incident_id": incident_id,
                "tipo": "incidente",
                "contenido": "Falta ANTHROPIC_API_KEY. Análisis de incidente no emitido.",
                "generado_por": self.model + " (Simulado)",
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            
        try:
            client = anthropic.AsyncAnthropic(api_key=self.api_key)
            resp = await client.messages.create(
                model=self.model,
                max_tokens=1000,
                temperature=0.1,
                system=CLAUDE_PROMPT_INJECTION_SYSTEM_PREFIX,
                messages=[{"role": "user", "content": prompt_filled}],
            )
            raw_res = resp.content[0].text if resp.content else "{}"
            
            clean_res = raw_res.strip()
            if clean_res.startswith("```json"): clean_res = clean_res[7:].strip()
            elif clean_res.startswith("```"): clean_res = clean_res[3:].strip()
            if clean_res.endswith("```"): clean_res = clean_res[:-3].strip()
                
            parsed = json.loads(clean_res)
            
            # Retornar AiMemo
            return {
                "id": memo_id,
                "incident_id": incident_id,
                "tipo": "incidente",
                "contenido": parsed.get("cronologia", "Análisis completado."),
                "detalles": parsed,
                "generado_por": self.model,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            logger.error(f"IncidentAnalyzer falló sobre {incident_id}: {e}")
            return {}
