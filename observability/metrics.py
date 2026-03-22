"""
Métricas Prometheus (NYXAR). Instrumentación in-situ puede importar y actualizar contadores/histogramas.
El PipelineCollector actualiza principalmente Gauges periódicos.
"""

from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram

# PIPELINE
EVENTOS_PROCESADOS = Counter(
    "NYXAR_eventos_total",
    "Total de eventos procesados",
    ["source", "tipo"],
)

EVENTOS_EN_COLA = Gauge(
    "NYXAR_eventos_cola",
    "Mensajes en stream Redis (XLEN)",
    ["stream"],
)

LATENCIA_ENRIQUECIMIENTO = Histogram(
    "NYXAR_enrichment_latency_seconds",
    "Latencia del proceso de enriquecimiento",
    ["resultado"],
    buckets=(0.001, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0),
)

# THREAT INTEL
CACHE_HIT_RATE = Gauge(
    "NYXAR_cache_hit_rate",
    "Ratio aproximado de cache hit en enrichment (0-1); 0 si no hay datos",
)

BLOCKLIST_SIZES = Gauge(
    "NYXAR_blocklist_size",
    "Cardinalidad de sets blocklist:* en Redis",
    ["lista"],
)

APIS_EXTERNAS_CALLS = Counter(
    "NYXAR_api_calls_total",
    "Llamadas a APIs externas de threat intel",
    ["api", "resultado"],
)

# SECURITY
INCIDENTES_ACTIVOS = Gauge(
    "NYXAR_incidentes_activos",
    "Incidentes no cerrados por severidad (Mongo)",
    ["severidad"],
)

HONEYPOT_HITS = Counter(
    "NYXAR_honeypot_hits_total",
    "Activaciones de honeypots por tipo",
    ["tipo_recurso"],
)

RISK_SCORES_DISTRIBUTION = Histogram(
    "NYXAR_risk_scores",
    "Muestras de risk_score de identidades (observar desde código de negocio)",
    buckets=(10.0, 20.0, 40.0, 60.0, 80.0, 100.0),
)

IDENTITIES_RISK_AVG = Gauge(
    "NYXAR_identities_risk_avg",
    "Promedio risk_score en colección identities (snapshot del collector)",
)

# SYSTEM
MONGODB_OPERATION_LATENCY = Histogram(
    "NYXAR_mongo_latency_seconds",
    "Latencia de operaciones MongoDB",
    ["operacion", "coleccion"],
    buckets=(0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0),
)

REDIS_OPERATION_LATENCY = Histogram(
    "NYXAR_redis_latency_seconds",
    "Latencia de operaciones Redis",
    ["operacion"],
    buckets=(0.001, 0.005, 0.01, 0.05, 0.1, 0.25, 0.5, 1.0),
)

SERVICIOS_ACTIVOS = Gauge(
    "NYXAR_servicios_activos",
    "1 si heartbeat Redis reciente; 0 si ausente",
    ["servicio"],
)

AI_TOKENS_USADOS = Counter(
    "NYXAR_ai_tokens_total",
    "Tokens consumidos de la API de Claude",
    ["tipo"],
)

AI_LLAMADAS = Counter(
    "NYXAR_ai_calls_total",
    "Llamadas a la API de Claude",
    ["tipo", "resultado"],
)

# Listas blocklist conocidas (feeds NYXAR); el collector ignora errores por lista ausente
BLOCKLIST_LISTAS = (
    "spamhaus_drop",
    "spamhaus_edrop",
    "feodo",
    "urlhaus",
    "threatfox",
    "misp_ips",
    "misp_domains",
    "misp_urls",
    "misp_hashes",
    "nyxar_external",
)

SERVICIOS_HEARTBEAT = (
    "collector",
    "enricher",
    "correlator",
    "notifier",
    "api",
    "observability",
    "ai_analyst",
)
