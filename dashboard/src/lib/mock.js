/**
 * Datos de demostración para desarrollo sin backend (solo con isDevDataEnabled).
 * Genera identidades, eventos recientes, métricas de status bar, alertas, incidentes y health.
 */

/** Serie 24h sintética alrededor del score actual. */
function mockRiskSpark24h(baseScore) {
  const b = Math.min(100, Math.max(0, Number(baseScore) || 0))
  return Array.from({ length: 24 }, (_, i) => ({
    timestamp: new Date(Date.now() - (23 - i) * 3600000).toISOString(),
    score: Math.round(
      Math.min(100, Math.max(0, b + (i - 12) * 2 + Math.sin(i * 0.45) * 14)),
    ),
  }))
}

function buildMockActivityHeatmap() {
  const cells = []
  for (let day = 0; day < 5; day += 1) {
    for (let hour = 8; hour <= 18; hour += 1) {
      cells.push({ day, hour, count: 2 + ((day * 3 + hour) % 9) })
    }
  }
  cells.push(
    { day: 5, hour: 11, count: 4 },
    { day: 5, hour: 15, count: 3 },
    { day: 6, hour: 10, count: 2 },
    { day: 6, hour: 16, count: 1 },
  )
  return cells
}

const DEMO_EVENTS_PER_HOUR = [3, 2, 1, 1, 2, 4, 9, 18, 24, 28, 30, 32, 31, 29, 27, 26, 24, 20, 14, 10, 7, 5, 4, 3]

/** Datos estáticos para charts cuando el buffer real es demasiado pequeño (solo dev). */
export const MOCK_CHARTS = {
  events_per_hour: DEMO_EVENTS_PER_HOUR.map((count, hour) => ({ hour, count })),
  threat_distribution: [
    { fuente: 'firewall', count: 220 },
    { fuente: 'dns', count: 165 },
    { fuente: 'proxy', count: 118 },
    { fuente: 'wazuh', count: 76 },
    { fuente: 'misp', count: 34 },
  ],
  activity_heatmap: buildMockActivityHeatmap(),
}

const MOCK_IDENTITY_BLUEPRINT = [
  ['Laura Méndez', 'Finanzas', 86, 38, 'PC-FIN-01', 'fin-pc-01', true],
  ['Carlos Ibarra', 'Finanzas', 22, -4, 'NB-FIN-02', 'nb-fin-02', false],
  ['Ana Ruiz', 'Contabilidad', 41, 6, 'PC-CTB-01', 'ctb-desk', false],
  ['Pedro Soto', 'Contabilidad', 18, 0, 'PC-CTB-03', 'ctb-03', false],
  ['Marcos Ventas', 'Ventas', 35, 5, 'TAB-VEN', 'tablet-04', false],
  ['Lucía Gómez', 'Ventas', 52, 12, 'LAP-VEN-11', 'ven-11', false],
  ['Diego Paredes', 'Ventas', 28, -1, 'PC-VEN-02', 'ven-02', false],
  ['Emilio CEO', 'Gerencia', 95, 80, 'MOBILE-CEO', 'iphone-emilio', true],
  ['Sofía Vega', 'Gerencia', 48, 3, 'TAB-GER', 'ipad-ger', false],
  ['Admin Sys', 'IT', 12, -2, 'MAC-IT', 'sys-admin-mac', true],
  ['Nico DevOps', 'IT', 44, 9, 'WS-DEV', 'dev-ws-01', false],
  ['Elena SecOps', 'IT', 78, 22, 'WS-SOC', 'soc-elena', true],
  ['Tomás Backup', 'IT', 8, 0, 'SRV-BKP', 'bkp-srv', false],
  ['Marta RRHH', 'RRHH', 25, 2, 'PC-RRHH', 'rrhh-01', false],
  ['Julián Talento', 'RRHH', 31, 4, 'NB-RRHH', 'rrhh-nb', false],
  ['Paula Brand', 'Marketing', 19, -3, 'MAC-MKT', 'mkt-mac', false],
  ['Hugo Campañas', 'Marketing', 62, 18, 'PC-MKT', 'mkt-pc-02', false],
  ['Victoria Legal', 'Gerencia', 55, 7, 'NB-LEG', 'legal-nb', false],
  ['Iker Soporte', 'IT', 33, 1, 'PC-SUP', 'sup-desk', false],
  ['Carmen Finanzas', 'Finanzas', 71, 15, 'NB-FIN-03', 'fin-carmen', false],
  ['Bruno Ventas', 'Ventas', 15, -5, 'PC-VEN-09', 'ven-09', false],
  ['Nadia Ops', 'IT', 59, 11, 'WS-NOC', 'noc-nadia', false],
  ['Óscar Auditor', 'Contabilidad', 67, 19, 'PC-AUD', 'aud-01', false],
]

const EXTERNO_POOL = [
  '185.220.101.44',
  'evil-c2.example.net',
  'pastebin.com',
  'tor-exit.mock.ip',
  'cdn.jsdelivr.net',
  'api.github.com',
  '45.33.32.156',
  'malware.test.invalid',
  'smtp.forward.net',
  'vpn.vendor.io',
]

const SOURCES_ROT = ['firewall', 'dns', 'proxy', 'wazuh', 'misp', 'firewall', 'dns']

const BASELINE_DOMAIN_POOL = [
  'microsoft.com',
  'office.com',
  'google.com',
  'slack.com',
  'zoom.us',
  'github.com',
  'atlassian.net',
  'salesforce.com',
  'adobe.com',
  'okta.com',
  'docusign.com',
  'dropbox.com',
]

/**
 * Baseline sintético por identidad (Zustand); la vista calcula desviaciones vs eventos en cliente.
 *
 * @param {{ id: string }[]} identities
 * @returns {Record<string, object>}
 */
export function buildIdentityBaselinesForMock(identities) {
  const out = {}
  for (let i = 0; i < identities.length; i += 1) {
    const id = identities[i].id
    if (!id) continue
    const startH = 8 + (i % 2)
    const startM = i % 3 === 0 ? 30 : 0
    const habitualStartMinutes = startH * 60 + startM
    const habitualEndMinutes = 18 * 60
    const nKnown = 5 + (i % 4)
    const known = []
    for (let k = 0; k < nKnown; k += 1) {
      known.push(BASELINE_DOMAIN_POOL[(i + k * 3) % BASELINE_DOMAIN_POOL.length])
    }
    out[String(id)] = {
      habitual_start_minutes: habitualStartMinutes,
      habitual_end_minutes: habitualEndMinutes,
      baseline_volume_mb: 60 + (i % 6) * 5 + (i % 4) * 2,
      known_domains: known,
    }
  }
  return out
}

function buildMockIdentities() {
  return MOCK_IDENTITY_BLUEPRINT.map((row, i) => {
    const [nombre_completo, area, risk_score, delta_2h, dispositivo, hostname, es_privilegiado] = row
    const third = 1 + Math.floor(i / 45)
    const fourth = 20 + (i % 200)
    const safeFourth = fourth > 254 ? 20 + (i % 40) : fourth
    const ip = `192.168.${third}.${safeFourth}`
    const score = Number(risk_score) || 0
    return {
      id: ip,
      ip_asociada: ip,
      nombre_completo,
      area,
      risk_score: score,
      delta_2h,
      dispositivo,
      hostname,
      es_privilegiado,
      last_seen_ts: new Date(Date.now() - (i % 9) * 120000).toISOString(),
      risk_sparkline_24h: mockRiskSpark24h(score),
    }
  })
}

/**
 * Eventos en orden cronológico ascendente (más antiguo primero), luego se invierte para el store (más nuevo primero).
 */
function buildMockEventSeries(identities, count) {
  const ips = identities.map((x) => x.id)
  const n = ips.length
  const chronological = []
  const base = Date.now() - count * 28000

  for (let i = 0; i < count; i += 1) {
    const ip = ips[i % n]
    const area = identities[i % n].area
    const source = SOURCES_ROT[i % SOURCES_ROT.length]
    const externo = { valor: EXTERNO_POOL[i % EXTERNO_POOL.length] }
    const risk = Math.min(100, Math.max(5, (i * 17 + (ip.charCodeAt(ip.length - 1) || 0)) % 97))
    const enrichment = { risk_score: risk }
    if (i % 23 === 0) enrichment.sospechoso = true
    if (i % 41 === 0) enrichment.malicioso = true
    if (i % 11 === 0) enrichment.pais = 'NL'
    if (i % 13 === 0) enrichment.asn = 'AS14061'

    chronological.push({
      id: `DEV-E-${String(i).padStart(4, '0')}`,
      source,
      timestamp: new Date(base + i * 26000 + (i % 5) * 4000).toISOString(),
      interno: { ip, area },
      externo,
      enrichment,
    })
  }
  return chronological.reverse()
}

function healthEntry(estado, mensaje, latMs, detalles) {
  return {
    estado,
    mensaje,
    latencia_ms: latMs,
    checked_at: new Date().toISOString(),
    detalles: detalles || undefined,
  }
}

function buildMockHealthThroughput(points = 36) {
  const out = []
  const now = Date.now()
  for (let i = points - 1; i >= 0; i -= 1) {
    const t = new Date(now - i * 120000)
    const isoMin = t.toISOString().slice(0, 16)
    out.push({
      minute: isoMin,
      count: 12 + Math.round(Math.sin(i * 0.35) * 8 + (i % 7)),
    })
  }
  return out
}

/**
 * Snapshot completo para setInitialState en desarrollo (timestamps frescos en cada llamada).
 */
export function buildDevMockInitialState() {
  const risk_identities = buildMockIdentities()
  const identity_baselines = buildIdentityBaselinesForMock(risk_identities)
  const hunting_identity_ids = [
    risk_identities[0]?.id,
    risk_identities[4]?.id,
  ].filter(Boolean)
  const last_events = buildMockEventSeries(risk_identities, 140)

  const highEventIds = last_events
    .filter((e) => (e.enrichment?.risk_score ?? 0) >= 72)
    .slice(0, 4)
    .map((e) => e.id)

  const alerts = [
    {
      id: 'DEV-AL-01',
      evento_original_id: highEventIds[0] || last_events[0]?.id,
      host_afectado: last_events[0]?.interno?.ip,
      timestamp: new Date().toISOString(),
      severidad: 'alta',
      tipo: 'correlación',
      titulo: 'Exfiltración sospechosa (mock)',
    },
    {
      id: 'DEV-AL-02',
      evento_original_id: highEventIds[1] || last_events[1]?.id,
      host_afectado: last_events[1]?.interno?.ip,
      timestamp: new Date(Date.now() - 120000).toISOString(),
      severidad: 'media',
      tipo: 'honeypot',
      titulo: 'Sondeo lateral detectado (mock)',
    },
    {
      id: 'DEV-AL-03',
      evento_original_id: highEventIds[2] || last_events[2]?.id,
      host_afectado: last_events[2]?.interno?.ip,
      timestamp: new Date(Date.now() - 300000).toISOString(),
      severidad: 'critica',
      tipo: 'malware',
      titulo: 'IOC MISP coincidente (mock)',
    },
  ]

  const incidents = [
    {
      id: 'DEV-INC-01',
      estado: 'abierto',
      severidad: 'alta',
      descripcion: 'Patrón de DNS tunneling en subred Finanzas (mock dev).',
      evento_original_id: highEventIds[0],
      timestamp: new Date(Date.now() - 600000).toISOString(),
    },
    {
      id: 'DEV-INC-02',
      estado: 'abierto',
      severidad: 'media',
      descripcion: 'Picos de tráfico saliente vs baseline (mock dev).',
      evento_original_id: highEventIds[1],
      timestamp: new Date(Date.now() - 900000).toISOString(),
    },
  ]

  const health_report = {
    estado_general: 'operativo',
    resumen: 'Mock dev: todos los chequeos dentro de parámetros simulados.',
    componentes: {
      redis: healthEntry('ok', 'PONG', 0.35, { mem: 'ok', clients: 12 }),
      mongodb: healthEntry('ok', 'Replica primaria', 1.2, { opcounters: 'normal' }),
      pipeline: healthEntry('ok', 'Lag < 2s', 0, { cola: 3 }),
    },
    servicios: {
      collector: healthEntry('ok', 'Ingesta estable', 4.5),
      enricher: healthEntry('ok', 'OTX + AbuseIPDB', 120),
      correlator: healthEntry('warning', 'Cola elevada leve', 80, { pendientes: 42 }),
      ai_analyst: healthEntry('ok', 'Modelo respondiendo', 890),
      notifier: healthEntry('ok', 'Sin reintentos', 15),
      api: healthEntry('ok', 'REST / WS', 2.1),
    },
    apis: {
      abuseipdb: healthEntry('ok', 'Cuota diaria OK', 95),
      otx: healthEntry('ok', 'Rate limit OK', 140),
      misp: healthEntry('ok', 'Último sync hace 3 min', 210),
      anthropic: healthEntry('ok', 'Disponible', 430),
    },
  }

  const ai_memos = [
    {
      id: 'MEM-01',
      texto: 'Mock: priorizar revisión de identidades IT con delta positivo en 2h.',
      timestamp: new Date(Date.now() - 3600000).toISOString(),
    },
    {
      id: 'MEM-02',
      texto: 'Mock: correlación sugiere campaña DNS similar a TAxxx en sector Finanzas.',
      timestamp: new Date(Date.now() - 7200000).toISOString(),
    },
  ]

  return {
    last_events,
    risk_identities,
    identity_baselines,
    hunting_identity_ids,
    ai_memos,
    stats: {
      eventos_por_min: 38,
      alertas_abiertas: alerts.length + incidents.length,
    },
    alerts,
    incidents,
    health_report,
    health_throughput: buildMockHealthThroughput(40),
  }
}

