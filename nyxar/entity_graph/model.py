"""
Modelo de datos del grafo de relaciones global (NYXAR V8).
Las estructuras reflejan el contrato MongoDB y el análisis en NetworkX en memoria.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional


class NodeType(Enum):
    """Entidades del universo NYXAR (vértices del grafo)."""

    IDENTITY = "identity"
    DEVICE = "device"
    AREA = "area"
    DOMAIN = "domain"
    IP_EXTERNAL = "ip_external"
    ASN = "asn"
    COUNTRY = "country"
    MALWARE = "malware"
    CAMPAIGN = "campaign"
    THREAT_ACTOR = "threat_actor"
    TIME_SLOT = "time_slot"
    DAY_PATTERN = "day_pattern"


class EdgeType(Enum):
    """Relaciones entre entidades (aristas tipadas)."""

    QUERIED = "queried"
    CONNECTED = "connected"
    RECEIVED = "received"
    SAME_DOMAIN = "same_domain"
    SAME_IP = "same_ip"
    SAME_TIMEFRAME = "same_timeframe"
    COOCCURRENCE = "cooccurrence"
    BELONGS_TO = "belongs_to"
    HOSTED_BY = "hosted_by"
    ASSOCIATED = "associated"
    PRECEDES = "precedes"
    CORRELATES = "correlates"


@dataclass
class Node:
    """Un nodo en el grafo de entidades de NYXAR."""

    id: str
    tipo: NodeType
    valor: str
    degree: int = 0
    betweenness: float = 0.0
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None
    total_events: int = 0
    risk_score: int = 0
    is_known_malicious: bool = False
    is_known_legitimate: bool = False
    tags: list[str] = field(default_factory=list)
    enrichment: Optional[dict[str, Any]] = None

    def node_id(self) -> str:
        """ID canónico del nodo para el grafo y como _id en MongoDB."""
        return f"{self.tipo.value}:{self.valor}"


@dataclass
class Edge:
    """Arista: relación entre dos entidades (por IDs canónicos de nodos)."""

    source_id: str
    target_id: str
    tipo: EdgeType
    weight: float = 1.0
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None
    event_count: int = 0
    is_new: bool = False
    days_since_first: int = 0
    context: dict[str, Any] = field(default_factory=dict)

    def edge_id(self) -> str:
        return f"{self.source_id}\u2192{self.tipo.value}\u2192{self.target_id}"


@dataclass
class GraphAnomalySignals:
    """
    Señales de anomalía estructural; alimentan al Unknown Detector, no son alertas finales.
    """

    new_edge_in_stable_cluster: bool = False
    cluster_stability_days: int = 0
    unexpected_bridge: bool = False
    clusters_connected: list[str] = field(default_factory=list)
    isomorphic_subgraph_found: bool = False
    historical_match_date: Optional[datetime] = None
    similarity_score: float = 0.0
    ephemeral_cluster: bool = False
    cluster_age_hours: int = 0
    sudden_centrality_increase: bool = False
    centrality_delta: float = 0.0
