import json
import os
from pathlib import Path

import anthropic

from shared.logger import get_logger
from shared.mongo_client import MongoClient

from threat_hunting.context_builder import hunting_context_to_prompt_chunks
from threat_hunting.models import HuntConclusion, Hypothesis, HuntingContext

logger = get_logger("threat_hunting.engine")

HYPOTHESES_COLLECTION = "hunting_hypotheses"


def _strip_json_fences(text: str) -> str:
    clean = text.strip()
    if clean.startswith("```json"):
        clean = clean[7:].strip()
    elif clean.startswith("```"):
        clean = clean[3:].strip()
    if clean.endswith("```"):
        clean = clean[:-3].strip()
    return clean


class HypothesisEngine:
    """
    Genera y refina hipótesis de threat hunting vía Claude.
    La persistencia y deduplicación usan la colección hunting_hypotheses si hay Mongo.
    """

    def __init__(
        self,
        mongo: MongoClient | None = None,
        api_key: str | None = None,
        model: str | None = None,
    ):
        self.mongo = mongo
        self.api_key = api_key if api_key is not None else os.getenv("ANTHROPIC_API_KEY", "")
        self.model = model or os.getenv("THREAT_HUNTING_MODEL", "claude-sonnet-4-20250514")
        self._prompt_dir = Path(__file__).resolve().parent / "prompts"

    def _read_prompt(self, name: str) -> str:
        path = self._prompt_dir / name
        if path.is_file():
            return path.read_text(encoding="utf-8")
        logger.warning("HypothesisEngine: falta prompt %s", path)
        return ""

    def _normalize_titulo(self, titulo: str) -> str:
        return titulo.lower().strip()

    async def _titulo_duplicado_activo(self, titulo: str) -> bool:
        if not self.mongo:
            return False
        t = self._normalize_titulo(titulo)
        if not t:
            return True
        col = self.mongo.db[HYPOTHESES_COLLECTION]
        q = {
            "estado": {"$in": ["nueva", "investigando", "confirmada"]},
            "titulo_normalizado": t,
        }
        return await col.count_documents(q) > 0

    async def generate_hypotheses(
        self,
        context: HuntingContext,
        *,
        hunter: str = "claude_autonomo",
        persist: bool = True,
    ) -> list[Hypothesis]:
        """
        Llama al modelo con el contexto y devuelve 3-5 hipótesis priorizadas.
        Omite títulos ya presentes en hunting_hypotheses (activas).
        """
        chunks = hunting_context_to_prompt_chunks(context)
        template = self._read_prompt("hypothesis.txt")
        user = (
            template.replace("{context}", chunks["context"])
            .replace("{threat_intel}", chunks["threat_intel"])
            .replace("{recent_incidents}", chunks["recent_incidents"])
        )

        if not self.api_key:
            logger.warning("HypothesisEngine.generate_hypotheses: falta ANTHROPIC_API_KEY")
            return []

        client = anthropic.AsyncAnthropic(api_key=self.api_key)
        resp = await client.messages.create(
            model=self.model,
            max_tokens=4096,
            temperature=0.2,
            system=(
                "Sos un Threat Hunter senior en NYXAR. "
                "Respondé únicamente el arreglo JSON pedido, sin texto adicional ni markdown."
            ),
            messages=[{"role": "user", "content": user}],
        )
        raw = resp.content[0].text if resp.content else "[]"
        try:
            data = json.loads(_strip_json_fences(raw))
        except json.JSONDecodeError:
            logger.error("HypothesisEngine.generate_hypotheses: respuesta no es JSON válido")
            return []

        if not isinstance(data, list):
            return []

        out: list[Hypothesis] = []
        seen_batch: set[str] = set()

        for item in data:
            if not isinstance(item, dict):
                continue
            titulo = (item.get("titulo") or "").strip()
            if not titulo:
                continue
            t_norm = self._normalize_titulo(titulo)
            if t_norm in seen_batch:
                continue
            if await self._titulo_duplicado_activo(titulo):
                continue
            seen_batch.add(t_norm)

            try:
                prioridad = int(item.get("prioridad") or 3)
            except (TypeError, ValueError):
                prioridad = 3
            prioridad = max(1, min(5, prioridad))

            queries = item.get("queries_sugeridas") or []
            if not isinstance(queries, list):
                queries = []

            hyp = Hypothesis(
                titulo=titulo,
                descripcion=(item.get("descripcion") or "").strip(),
                tecnica_mitre=(item.get("tecnica_mitre") or "").strip() or "T0000",
                prioridad=prioridad,
                queries_sugeridas=[str(q) for q in queries if q],
                hunter=hunter,
            )
            out.append(hyp)

        if persist and self.mongo and out:
            col = self.mongo.db[HYPOTHESES_COLLECTION]
            for h in out:
                doc = h.model_dump(mode="json")
                doc["titulo_normalizado"] = self._normalize_titulo(h.titulo)
                await col.insert_one(doc)

        return out

    async def refine_hypothesis(
        self,
        hypothesis: Hypothesis,
        resultados_parciales: list[dict],
    ) -> Hypothesis:
        """
        Interpreta resultados parciales y devuelve una copia ajustada de la hipótesis
        (estado, descripción o queries adicionales) sin cerrar el hunt.
        """
        findings_tmpl = self._read_prompt("findings.txt")
        hyp_str = json.dumps(hypothesis.model_dump(mode="json"), ensure_ascii=False, indent=2)
        res_str = json.dumps(resultados_parciales, ensure_ascii=False, indent=2)
        base = findings_tmpl.replace("{hypothesis}", hyp_str).replace("{results}", res_str)
        user = (
            "FASE INTERMEDIA: no es la conclusión final. "
            "Completá el JSON del template y agregá si aplica:\n"
            '- "estado_sugerido": "nueva" | "investigando" | "confirmada" | "descartada"\n'
            '- "descripcion_actualizada": texto si refinás la hipótesis\n\n'
            f"{base}"
        )

        if not self.api_key:
            return hypothesis

        client = anthropic.AsyncAnthropic(api_key=self.api_key)
        resp = await client.messages.create(
            model=self.model,
            max_tokens=2048,
            temperature=0.15,
            system="Analista SOC. Solo JSON válido, sin markdown.",
            messages=[{"role": "user", "content": user}],
        )
        raw = resp.content[0].text if resp.content else "{}"
        try:
            parsed = json.loads(_strip_json_fences(raw))
        except json.JSONDecodeError:
            logger.warning("HypothesisEngine.refine_hypothesis: JSON inválido, sin cambios")
            return hypothesis

        updates = hypothesis.model_copy(deep=True)
        est = parsed.get("estado_sugerido")
        if est in ("nueva", "investigando", "confirmada", "descartada"):
            updates.estado = est
        desc = parsed.get("descripcion_actualizada")
        if isinstance(desc, str) and desc.strip():
            updates.descripcion = desc.strip()
        prox = parsed.get("proximos_pasos")
        if isinstance(prox, list) and prox:
            extra = [str(x) for x in prox if x]
            merged = list(updates.queries_sugeridas or []) + extra
            updates.queries_sugeridas = list(dict.fromkeys(merged))
        return updates

    async def conclude_hunt(
        self,
        hypothesis: Hypothesis,
        todos_los_resultados: list[dict],
    ) -> HuntConclusion:
        """Cierra el hunt mapeando la salida del prompt findings al modelo HuntConclusion."""
        findings_tmpl = self._read_prompt("findings.txt")
        hyp_str = json.dumps(hypothesis.model_dump(mode="json"), ensure_ascii=False, indent=2)
        res_str = json.dumps(todos_los_resultados, ensure_ascii=False, indent=2)
        base = findings_tmpl.replace("{hypothesis}", hyp_str).replace("{results}", res_str)
        user = f"FASE FINAL: conclusión definitiva del hunt.\n\n{base}"

        if not self.api_key:
            return HuntConclusion(
                hypothesis_id=hypothesis.id,
                encontrado=False,
                evidencia=[],
                confianza="baja",
                iocs_nuevos=[],
                crear_incidente=False,
                resumen="Falta ANTHROPIC_API_KEY; no se generó conclusión.",
            )

        client = anthropic.AsyncAnthropic(api_key=self.api_key)
        resp = await client.messages.create(
            model=self.model,
            max_tokens=2048,
            temperature=0.1,
            system="Analista SOC. Solo JSON válido según el template del usuario.",
            messages=[{"role": "user", "content": user}],
        )
        raw = resp.content[0].text if resp.content else "{}"
        try:
            parsed = json.loads(_strip_json_fences(raw))
        except json.JSONDecodeError:
            return HuntConclusion(
                hypothesis_id=hypothesis.id,
                encontrado=False,
                evidencia=[],
                confianza="baja",
                iocs_nuevos=[],
                crear_incidente=False,
                resumen="No se pudo parsear la respuesta del modelo.",
            )

        clues = parsed.get("evidencia_clave") or []
        evidencia = [{"descripcion": str(x)} for x in clues if x]

        conf = parsed.get("confianza") or "baja"
        if conf not in ("alta", "media", "baja"):
            conf = "baja"

        iocs_raw = parsed.get("iocs_nuevos") or []
        iocs_nuevos = [str(x) for x in iocs_raw if x]

        resumen = (parsed.get("justificacion") or "").strip()
        if not resumen:
            resumen = "Sin justificación textual del modelo."

        return HuntConclusion(
            hypothesis_id=hypothesis.id,
            encontrado=bool(parsed.get("encontrado")),
            evidencia=evidencia,
            confianza=conf,
            iocs_nuevos=iocs_nuevos,
            crear_incidente=bool(parsed.get("crear_incidente")),
            resumen=resumen,
        )

    async def formalize_manual_hypothesis(
        self,
        descripcion: str,
        *,
        hunter: str = "analista_manual",
        persist: bool = True,
    ) -> Hypothesis | None:
        """
        Convierte texto libre del analista en un objeto Hypothesis vía Claude.
        Retorna None si falta API key, JSON inválido o título duplicado activo.
        """
        descripcion = (descripcion or "").strip()
        if not descripcion:
            return None

        path = self._prompt_dir / "formalize_hypothesis.txt"
        template = path.read_text(encoding="utf-8") if path.is_file() else ""
        if not template:
            logger.warning("HypothesisEngine: falta formalize_hypothesis.txt")
            return None

        user = template.replace("{descripcion}", descripcion)
        if not self.api_key:
            logger.warning("HypothesisEngine.formalize_manual_hypothesis: falta ANTHROPIC_API_KEY")
            return None

        client = anthropic.AsyncAnthropic(api_key=self.api_key)
        try:
            resp = await client.messages.create(
                model=self.model,
                max_tokens=2048,
                temperature=0.2,
                system="Solo JSON válido según el template, sin markdown.",
                messages=[{"role": "user", "content": user}],
            )
            raw = resp.content[0].text if resp.content else "{}"
            data = json.loads(_strip_json_fences(raw))
        except Exception as e:
            logger.error("HypothesisEngine.formalize_manual_hypothesis: %s", e)
            return None

        if not isinstance(data, dict):
            return None

        titulo = (data.get("titulo") or "").strip()
        if not titulo:
            return None
        if await self._titulo_duplicado_activo(titulo):
            return None

        try:
            prioridad = int(data.get("prioridad") or 3)
        except (TypeError, ValueError):
            prioridad = 3
        prioridad = max(1, min(5, prioridad))

        qs = data.get("queries_sugeridas") or []
        if not isinstance(qs, list):
            qs = []

        hyp = Hypothesis(
            titulo=titulo,
            descripcion=(data.get("descripcion") or "").strip(),
            tecnica_mitre=(data.get("tecnica_mitre") or "").strip() or "T0000",
            prioridad=prioridad,
            queries_sugeridas=[str(x) for x in qs if x],
            hunter=hunter,
        )

        if persist and self.mongo:
            doc = hyp.model_dump(mode="json")
            doc["titulo_normalizado"] = self._normalize_titulo(hyp.titulo)
            await self.mongo.db[HYPOTHESES_COLLECTION].insert_one(doc)

        return hyp
