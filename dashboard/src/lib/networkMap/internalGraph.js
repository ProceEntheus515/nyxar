import { areaToClusterKey } from './clusterAnchors'

const FIVE_MIN_MS = 5 * 60 * 1000

/**
 * @param {number} score
 * @returns {number} radio en px (spec F09 mapa)
 */
export function nodeRadiusForScore(score) {
  const s = Number(score) || 0
  if (s > 80) return 20
  if (s > 60) return 16
  if (s >= 20) return 12
  return 8
}

/**
 * @param {object} [enrichment]
 * @param {number} [eventRiskScore]
 * @returns {'normal' | 'suspicious' | 'malicious'}
 */
export function linkThreatLevel(enrichment, eventRiskScore) {
  const e = enrichment || {}
  const rs = Number(eventRiskScore)
  if (e.malicioso === true || String(e.threat || '').toLowerCase().includes('malic')) {
    return 'malicious'
  }
  if (Number.isFinite(rs) && rs >= 85) return 'malicious'
  if (e.sospechoso === true || e.suspicious === true) return 'suspicious'
  if (Number.isFinite(rs) && rs >= 55) return 'suspicious'
  return 'normal'
}

export function internoNodeId(ev) {
  const i = ev?.interno
  if (!i) return null
  return String(i.ip || i.id_usuario || i.ip_asociada || '').trim() || null
}

/**
 * Identidades → nodos con metadata de cluster (sin posición).
 *
 * @param {Record<string, object>} identitiesMap
 * @returns {Map<string, object>}
 */
export function buildIdentityNodes(identitiesMap) {
  const out = new Map()
  for (const row of Object.values(identitiesMap || {})) {
    const id = String(row.id || row.ip_asociada || '')
    if (!id) continue
    const score = Number(row.risk_score) || 0
    const area = row.area || '—'
    const clusterKey = areaToClusterKey(area)
    out.set(id, {
      id,
      identity: row,
      area,
      clusterKey,
      score,
      radius: nodeRadiusForScore(score),
      nombre: row.nombre_completo || id,
    })
  }
  return out
}

/**
 * Aristas solo entre nodos internos: cadena temporal por eventos recientes
 * (mismo buffer que la ventana 5 min). Sin nodos externos.
 *
 * @param {object[]} events
 * @param {Set<string>} validNodeIds
 * @returns {{ source: string, target: string, volume: number, level: string, lastSource: string }[]}
 */
export function buildInternalLinksFromEvents(events, validNodeIds) {
  const now = Date.now()
  const recent = (events || []).filter((ev) => {
    try {
      return now - new Date(ev.timestamp).getTime() <= FIVE_MIN_MS
    } catch {
      return false
    }
  })
  const sorted = [...recent].sort(
    (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime(),
  )

  const agg = new Map()
  let prevId = null

  for (const ev of sorted) {
    const nid = internoNodeId(ev)
    if (!nid || !validNodeIds.has(nid)) {
      prevId = null
      continue
    }
    const enr = ev.enrichment || {}
    const evRisk = Number(enr.risk_score)
    const level = linkThreatLevel(enr, evRisk)

    if (prevId && prevId !== nid) {
      const a = prevId < nid ? prevId : nid
      const b = prevId < nid ? nid : prevId
      const key = `${a}|${b}`
      const cur = agg.get(key) || {
        source: a,
        target: b,
        volume: 0,
        level: 'normal',
        lastSource: null,
      }
      cur.volume += 1
      const rank = { normal: 0, suspicious: 1, malicious: 2 }
      if (rank[level] > rank[cur.level]) cur.level = level
      cur.lastSource = ev.source || 'interno'
      agg.set(key, cur)
    }
    prevId = nid
  }

  return [...agg.values()]
}

/**
 * Nodos con actividad en ventana (aparecen en al menos un evento reciente).
 *
 * @param {object[]} events
 * @param {Set<string>} validNodeIds
 */
export function activeNodeIdsInWindow(events, validNodeIds) {
  const now = Date.now()
  const set = new Set()
  for (const ev of events || []) {
    try {
      if (now - new Date(ev.timestamp).getTime() > FIVE_MIN_MS) continue
    } catch {
      continue
    }
    const nid = internoNodeId(ev)
    if (nid && validNodeIds.has(nid)) set.add(nid)
  }
  return set
}
