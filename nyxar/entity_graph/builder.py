"""
Constructor incremental del grafo a partir del stream de eventos enriquecidos (V8 U02).
Grafo en NetworkX (ventana activa ~24 h en memoria) + persistencia en MongoDB.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any, Optional

import networkx as nx
from motor.motor_asyncio import AsyncIOMotorDatabase

from nyxar.entity_graph.model import EdgeType, NodeType

if TYPE_CHECKING:
    from shared.redis_bus import RedisBus

logger = logging.getLogger(__name__)

try:
    from shared.logger import get_logger

    logger = get_logger("entity_graph.builder")
except ImportError:
    pass

# Dominios muy comunes: no generar aristas SAME_DOMAIN (ruido / privacidad innecesaria).
_KNOWN_LEGITIMATE_DOMAINS = frozenset(
    {
        "google.com",
        "www.google.com",
        "gstatic.com",
        "googleapis.com",
        "microsoft.com",
        "www.microsoft.com",
        "live.com",
        "office.com",
        "microsoftonline.com",
        "cloudflare.com",
        "apple.com",
        "icloud.com",
        "facebook.com",
        "amazonaws.com",
        "windows.net",
    }
)

ARROW = "\u2192"
CONSUMER_GROUP = "entity-graph-v8"
CONSUMER_NAME = "graph-builder-1"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(dt: Any) -> datetime:
    if isinstance(dt, datetime):
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    return _utcnow()


class GraphBuilder:
    """
    Construye y mantiene el grafo de entidades: MongoDB (histórico) + NetworkX (activo).
    """

    def __init__(
        self,
        db: AsyncIOMotorDatabase,
        redis_bus: Optional[RedisBus],
    ) -> None:
        self.db = db
        self.redis = redis_bus
        self.G = nx.DiGraph()
        self.G_undirected: Optional[nx.Graph] = None
        self._dirty = False

    async def start(self) -> None:
        """Carga desde Mongo, consume enriched y análisis periódico."""
        if self.redis is None:
            raise RuntimeError("GraphBuilder.start requiere RedisBus para el stream enriquecido")
        await self._load_from_mongo()
        await self.redis.create_consumer_group(
            self.redis.STREAM_ENRICHED,
            CONSUMER_GROUP,
            "0",
        )
        await asyncio.gather(
            self._consume_events(),
            self._periodic_analysis(),
        )

    async def _load_from_mongo(self) -> None:
        cutoff = _utcnow() - timedelta(hours=24)

        async for node_doc in self.db.entity_graph_nodes.find({"last_seen": {"$gte": cutoff}}):
            nid = node_doc["_id"]
            attrs = {k: v for k, v in node_doc.items() if k != "_id"}
            self.G.add_node(nid, **attrs)

        async for edge_doc in self.db.entity_graph_edges.find({"last_seen": {"$gte": cutoff}}):
            src, tgt = edge_doc["source_id"], edge_doc["target_id"]
            ctx = edge_doc.get("context") or {}
            if not isinstance(ctx, dict):
                ctx = {}
            self.G.add_edge(
                src,
                tgt,
                tipo=edge_doc.get("tipo"),
                weight=float(edge_doc.get("weight", 1.0)),
                first_seen=edge_doc.get("first_seen"),
                last_seen=edge_doc.get("last_seen"),
                event_count=int(edge_doc.get("event_count", 0)),
                is_new=bool(edge_doc.get("is_new", False)),
                days_since_first=int(edge_doc.get("days_since_first", 0)),
                **ctx,
            )

        logger.info(
            "Grafo cargado: %s nodos, %s aristas",
            self.G.number_of_nodes(),
            self.G.number_of_edges(),
        )

    async def process_event(self, evento: dict) -> list[str]:
        """
        Un evento enriquecido (dict, p. ej. desde Redis) actualiza nodos y aristas.
        Devuelve códigos/mensajes de anomalías estructurales simples.
        """
        anomalies: list[str] = []
        interno = evento.get("interno") or {}
        externo = evento.get("externo") or {}
        if not isinstance(interno, dict):
            interno = {}
        if not isinstance(externo, dict):
            externo = {}

        ext_val = str(externo.get("valor") or "").strip()
        if not ext_val:
            return anomalies

        enrichment = evento.get("enrichment")
        if enrichment is not None and not isinstance(enrichment, dict):
            enrichment = {}

        ext_tipo = str(externo.get("tipo") or "dominio").lower()
        if ext_tipo == "ip":
            external_id = f"{NodeType.IP_EXTERNAL.value}:{ext_val}"
            ext_node_type = NodeType.IP_EXTERNAL
        else:
            external_id = f"{NodeType.DOMAIN.value}:{ext_val}"
            ext_node_type = NodeType.DOMAIN

        usuario = str(interno.get("usuario") or "desconocido").strip() or "desconocido"
        area = str(interno.get("area") or "desconocido").strip() or "desconocido"
        identity_id = f"{NodeType.IDENTITY.value}:{usuario}"
        area_id = f"{NodeType.AREA.value}:{area}"

        now = _utcnow()
        risk = evento.get("risk_score")

        await self._upsert_node(
            identity_id,
            NodeType.IDENTITY,
            usuario,
            now,
            enrichment=None,
            risk_score=risk if isinstance(risk, int) else None,
        )
        await self._upsert_node(
            external_id,
            ext_node_type,
            ext_val,
            now,
            enrichment=enrichment if isinstance(enrichment, dict) else None,
            risk_score=risk if isinstance(risk, int) else None,
        )
        await self._upsert_node(
            area_id,
            NodeType.AREA,
            area,
            now,
            enrichment=None,
            risk_score=None,
        )

        if isinstance(enrichment, dict) and enrichment.get("asn") is not None:
            asn_raw = enrichment.get("asn")
            asn_str = str(asn_raw).strip()
            if asn_str:
                asn_id = f"{NodeType.ASN.value}:{asn_str}"
                await self._upsert_node(asn_id, NodeType.ASN, asn_str, now)
                await self._upsert_edge(external_id, asn_id, EdgeType.HOSTED_BY, now)

        if isinstance(enrichment, dict) and enrichment.get("pais_origen"):
            country_code = str(enrichment["pais_origen"]).strip()
            if country_code:
                country_id = f"{NodeType.COUNTRY.value}:{country_code}"
                await self._upsert_node(country_id, NodeType.COUNTRY, country_code, now)
                asn_for_country = str(enrichment.get("asn") or "").strip()
                if asn_for_country:
                    asn_id = f"{NodeType.ASN.value}:{asn_for_country}"
                    await self._upsert_edge(asn_id, country_id, EdgeType.HOSTED_BY, now)

        source = str(evento.get("source") or "")
        edge_type = EdgeType.QUERIED if source == "dns" else EdgeType.CONNECTED
        is_new_edge = await self._upsert_edge(identity_id, external_id, edge_type, now)

        await self._upsert_edge(identity_id, area_id, EdgeType.BELONGS_TO, now)

        if is_new_edge:
            anomaly = await self._check_new_edge_anomaly(identity_id, external_id, now)
            if anomaly:
                anomalies.append(anomaly)

        await self._update_cooccurrence(identity_id, external_id, now)

        self._dirty = True
        return anomalies

    def _domain_skip_cooccurrence(self, domain_id: str) -> bool:
        if not self.G.has_node(domain_id):
            return False
        data = self.G.nodes[domain_id]
        if data.get("is_known_legitimate"):
            return True
        valor = str(data.get("valor") or "").lower()
        return valor in _KNOWN_LEGITIMATE_DOMAINS

    async def _upsert_node(
        self,
        node_id: str,
        tipo: NodeType,
        valor: str,
        timestamp: datetime,
        enrichment: Optional[dict[str, Any]],
        risk_score: Optional[int],
    ) -> bool:
        is_new = not self.G.has_node(node_id)

        tags: list[str] = []
        is_mal = False
        is_legit = False
        if isinstance(enrichment, dict):
            tags = list(enrichment.get("tags") or [])
            if not isinstance(tags, list):
                tags = []
            rep = str(enrichment.get("reputacion") or "")
            if rep == "malicioso":
                is_mal = True
            if tipo == NodeType.DOMAIN and valor.lower() in _KNOWN_LEGITIMATE_DOMAINS:
                is_legit = True

        if is_new:
            self.G.add_node(
                node_id,
                tipo=tipo.value,
                valor=valor,
                first_seen=timestamp,
                last_seen=timestamp,
                total_events=1,
                degree=0,
                betweenness=0.0,
                is_new=True,
                enrichment=enrichment,
                risk_score=int(risk_score) if risk_score is not None else 0,
                is_known_malicious=is_mal,
                is_known_legitimate=is_legit,
                tags=tags,
            )
        else:
            n = self.G.nodes[node_id]
            n["last_seen"] = timestamp
            n["total_events"] = int(n.get("total_events", 0)) + 1
            n["is_new"] = False
            if enrichment is not None:
                n["enrichment"] = enrichment
            if risk_score is not None:
                n["risk_score"] = max(int(n.get("risk_score", 0)), int(risk_score))
            n["is_known_malicious"] = bool(n.get("is_known_malicious")) or is_mal
            n["is_known_legitimate"] = bool(n.get("is_known_legitimate")) or is_legit
            if tags:
                prev = n.get("tags") or []
                if not isinstance(prev, list):
                    prev = []
                merged = list(dict.fromkeys([*prev, *tags]))
                n["tags"] = merged

        set_doc: dict[str, Any] = {
            "last_seen": timestamp,
            "valor": valor,
            "tipo": tipo.value,
            "is_known_malicious": self.G.nodes[node_id].get("is_known_malicious", False),
            "is_known_legitimate": self.G.nodes[node_id].get("is_known_legitimate", False),
            "tags": self.G.nodes[node_id].get("tags", []),
            "risk_score": int(self.G.nodes[node_id].get("risk_score", 0)),
        }
        if enrichment is not None:
            set_doc["enrichment"] = enrichment

        await self.db.entity_graph_nodes.update_one(
            {"_id": node_id},
            {
                "$set": set_doc,
                "$inc": {"total_events": 1},
                "$setOnInsert": {
                    "_id": node_id,
                    "first_seen": timestamp,
                    "degree": 0,
                    "betweenness": 0.0,
                    "is_new": True,
                },
            },
            upsert=True,
        )
        return is_new

    async def _upsert_edge(
        self,
        source: str,
        target: str,
        tipo: EdgeType,
        timestamp: datetime,
    ) -> bool:
        edge_id = f"{source}{ARROW}{tipo.value}{ARROW}{target}"
        is_new = not self.G.has_edge(source, target)

        if is_new:
            self.G.add_edge(
                source,
                target,
                tipo=tipo.value,
                weight=1.0,
                first_seen=timestamp,
                last_seen=timestamp,
                event_count=1,
                is_new=True,
                days_since_first=0,
            )
        else:
            edge_data = self.G[source][target]
            edge_data["weight"] = min(float(edge_data.get("weight", 1.0)) + 0.1, 100.0)
            edge_data["last_seen"] = timestamp
            edge_data["event_count"] = int(edge_data.get("event_count", 0)) + 1
            edge_data["is_new"] = False
            first_seen = edge_data.get("first_seen", timestamp)
            first_seen = _as_utc(first_seen)
            edge_data["days_since_first"] = max(0, (timestamp - first_seen).days)

        await self._persist_edge_mongo(edge_id, source, target, tipo, timestamp, is_new)
        return is_new

    async def _persist_edge_mongo(
        self,
        edge_id: str,
        source: str,
        target: str,
        tipo: EdgeType,
        timestamp: datetime,
        _is_new_memory: bool,
    ) -> None:
        existing = await self.db.entity_graph_edges.find_one({"_id": edge_id})
        if existing is None:
            await self.db.entity_graph_edges.insert_one(
                {
                    "_id": edge_id,
                    "source_id": source,
                    "target_id": target,
                    "tipo": tipo.value,
                    "weight": 1.0,
                    "first_seen": timestamp,
                    "last_seen": timestamp,
                    "event_count": 1,
                    "is_new": True,
                    "days_since_first": 0,
                    "context": {},
                }
            )
            return

        first = _as_utc(existing.get("first_seen", timestamp))
        days = max(0, (timestamp - first).days)
        new_weight = min(float(existing.get("weight", 1.0)) + 0.1, 100.0)
        await self.db.entity_graph_edges.update_one(
            {"_id": edge_id},
            {
                "$set": {
                    "last_seen": timestamp,
                    "source_id": source,
                    "target_id": target,
                    "tipo": tipo.value,
                    "weight": new_weight,
                    "event_count": int(existing.get("event_count", 0)) + 1,
                    "is_new": False,
                    "days_since_first": days,
                }
            },
        )

    async def _check_new_edge_anomaly(
        self,
        source: str,
        target: str,
        now: datetime,
    ) -> Optional[str]:
        if not self.G.has_node(source) or not self.G.has_node(target):
            return None
        s_first = _as_utc(self.G.nodes[source].get("first_seen", now))
        t_first = _as_utc(self.G.nodes[target].get("first_seen", now))
        source_age = max(0, (now - s_first).days)
        target_age = max(0, (now - t_first).days)

        if source_age > 7 and target_age > 7:
            return (
                f"NUEVA_RELACION_ENTRE_ENTIDADES_CONOCIDAS: "
                f"{source} (vista hace {source_age}d) conectó con "
                f"{target} (vista hace {target_age}d) por primera vez"
            )
        return None

    async def _update_cooccurrence(
        self,
        identity_id: str,
        external_id: str,
        now: datetime,
    ) -> None:
        if not external_id.startswith(f"{NodeType.DOMAIN.value}:"):
            return
        if self._domain_skip_cooccurrence(external_id):
            return

        cutoff = now - timedelta(hours=24)
        other_identities: list[str] = []
        for n, d in self.G.nodes(data=True):
            if d.get("tipo") != NodeType.IDENTITY.value or n == identity_id:
                continue
            if not self.G.has_edge(n, external_id):
                continue
            last_seen = d.get("last_seen")
            if last_seen is None:
                continue
            if _as_utc(last_seen) > cutoff:
                other_identities.append(n)

        for other_id in other_identities:
            await self._upsert_edge(identity_id, other_id, EdgeType.SAME_DOMAIN, now)

    async def _consume_events(self) -> None:
        assert self.redis is not None
        stream = self.redis.STREAM_ENRICHED
        while True:
            try:
                batch = await self.redis.consume_events(
                    stream,
                    CONSUMER_GROUP,
                    CONSUMER_NAME,
                    count=20,
                )
                for msg_id, evento in batch:
                    try:
                        await self.process_event(evento)
                    except Exception as e:
                        logger.exception("process_event falló: %s", e)
                    await self.redis.acknowledge(stream, CONSUMER_GROUP, msg_id)
                if not batch:
                    await asyncio.sleep(0.3)
            except Exception as e:
                logger.warning("consume_events: %s — reintento en 2s", e)
                await asyncio.sleep(2.0)

    async def _periodic_analysis(self) -> None:
        while True:
            await asyncio.sleep(900)
            if self._dirty:
                await self._recalculate_metrics()
                self._dirty = False

    async def _recalculate_metrics(self) -> None:
        if self.G.number_of_nodes() < 3:
            return

        try:
            k = min(50, self.G.number_of_nodes())
            centrality = nx.betweenness_centrality(self.G, normalized=True, k=k)
            for node_id, score in centrality.items():
                old_score = float(self.G.nodes[node_id].get("betweenness", 0.0))
                self.G.nodes[node_id]["betweenness"] = score
                deg = int(self.G.degree(node_id))
                self.G.nodes[node_id]["degree"] = deg

                if score > old_score * 2 and score > 0.1 and self.redis is not None:
                    try:
                        await self.redis.publish_alert(
                            "dashboard:alerts",
                            {
                                "tipo": "graph_anomaly",
                                "subtipo": "sudden_centrality",
                                "node": node_id,
                                "old_score": old_score,
                                "new_score": score,
                            },
                        )
                    except Exception as e:
                        logger.warning("publish_alert graph_anomaly: %s", e)

                await self.db.entity_graph_nodes.update_one(
                    {"_id": node_id},
                    {"$set": {"betweenness": score, "degree": deg}},
                )
        except Exception as e:
            logger.warning("Error calculando betweenness: %s", e)

        self.G_undirected = self.G.to_undirected()
        logger.info(
            "Métricas del grafo actualizadas: %sN x %sE",
            self.G.number_of_nodes(),
            self.G.number_of_edges(),
        )
