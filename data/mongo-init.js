// Time Series Collection para eventos — compresión automática + queries por rango optimizadas
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
