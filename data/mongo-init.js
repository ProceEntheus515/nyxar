// Time Series Collection para eventos — compresión automática + queries por rango optimizadas
// S05: el TTL sobre timeField ya limita retención (~30 días); no duplicar índice TTL en timestamp
// (MongoDB time series no admite bien un segundo TTL redundante sobre el mismo campo).
db.createCollection("events", {
  timeseries: {
    timeField: "timestamp",
    metaField: "meta",       // { source, area, usuario, ip }
    granularity: "seconds"
  },
  expireAfterSeconds: 2592000  // auto-elimina eventos de más de 30 días
})
db.events.createIndex({ "meta.ip": 1, "timestamp": -1 })
db.events.createIndex({ "meta.source": 1, "timestamp": -1 })
db.events.createIndex({ "externo.valor": 1 })
db.events.createIndex({ "risk_score": -1 })

// Identidades con baseline embebido (un solo documento por usuario)
db.createCollection("identities")
db.identities.createIndex({ "id": 1 }, { unique: true })
db.identities.createIndex({ "risk_score_actual": -1 })
db.identities.createIndex({ "area": 1 })
// S05: índice parcial — solo documentos con ultima_actividad (modelo API); el umbral "24 h" no puede
// fijarse en partialFilterExpression (quedaría congelado al crear el índice), por eso solo exigimos fecha.
db.identities.createIndex(
  { "risk_score_actual": -1 },
  {
    name: "identities_risk_score_actual_con_actividad_partial",
    partialFilterExpression: {
      ultima_actividad: { $exists: true, $type: "date" },
    },
  }
)

// Incidentes
db.createCollection("incidents")
db.incidents.createIndex({ "estado": 1, "severidad": 1 })
db.incidents.createIndex({ "created_at": -1 })

// Memos de IA
db.createCollection("ai_memos")
db.ai_memos.createIndex({ "created_at": -1 })
db.ai_memos.createIndex({ "prioridad": 1 })

// Honeypot hits — sin TTL, retener siempre como evidencia
db.createCollection("honeypot_hits")
db.honeypot_hits.createIndex({ "timestamp": -1 })

// S13: audit de seguridad del producto (append-only por convención; sin rutas de borrado en API)
db.createCollection("security_audit_log")
db.security_audit_log.createIndex({ "timestamp": -1 })

// --- NYXAR V8: grafo, memoria profunda, hallazgos emergentes ---
db.createCollection("entity_graph_nodes")
db.entity_graph_nodes.createIndex({ "tipo": 1, "risk_score": -1 })
db.entity_graph_nodes.createIndex({ "betweenness": -1 })
db.entity_graph_nodes.createIndex({ "is_new": 1, "first_seen": -1 })

db.createCollection("entity_graph_edges")
db.entity_graph_edges.createIndex({ "source_id": 1 })
db.entity_graph_edges.createIndex({ "target_id": 1 })
db.entity_graph_edges.createIndex({ "tipo": 1, "is_new": 1 })
db.entity_graph_edges.createIndex({ "weight": -1 })

db.createCollection("behavior_fingerprints")
db.behavior_fingerprints.createIndex({ "created_at": -1 })

db.createCollection("unknown_findings")
db.unknown_findings.createIndex({ "created_at": -1 })
db.unknown_findings.createIndex({ "status": 1 })

db.createCollection("emergent_taxonomy")
db.emergent_taxonomy.createIndex({ "slug": 1 }, { unique: true })
db.emergent_taxonomy.createIndex({ "updated_at": -1 })
