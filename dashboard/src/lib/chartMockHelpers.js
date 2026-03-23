import { isDevDataEnabled } from './devData'
import { MOCK_CHARTS } from './mock'

/** Serie 24h de scores alrededor de un valor base (sin aleatoriedad). */
export function makeRiskSparkline24h(baseScore) {
  const b = Math.min(100, Math.max(0, Number(baseScore) || 0))
  return Array.from({ length: 24 }, (_, i) => ({
    timestamp: new Date(Date.now() - (23 - i) * 3600000).toISOString(),
    score: Math.round(
      Math.min(100, Math.max(0, b + (i - 12) * 2 + Math.sin(i * 0.45) * 14)),
    ),
  }))
}

/**
 * Buckets por hora desde eventos reales.
 * @param {Array<{ timestamp?: string }>} events
 * @returns {{ hour: number, count: number }[]}
 */
export function buildEventsPerHour(events) {
  const by = Array(24).fill(0)
  for (const e of events || []) {
    try {
      const h = new Date(e.timestamp).getHours()
      if (h >= 0 && h <= 23) by[h] += 1
    } catch {
      /* ignore */
    }
  }
  return by.map((count, hour) => ({ hour, count }))
}

/**
 * Si hay pocos eventos en buffer, mostramos mock para que el chart no quede vacío.
 */
export function eventsPerHourForChart(events, minTotal = 8) {
  const fromEvents = buildEventsPerHour(events)
  const sum = fromEvents.reduce((s, x) => s + x.count, 0)
  if (sum >= minTotal) return fromEvents
  if (isDevDataEnabled) return MOCK_CHARTS.events_per_hour
  return fromEvents
}

/**
 * Agrega conteos por fuente (string libre → label).
 */
export function buildThreatDistribution(events) {
  const m = new Map()
  for (const e of events || []) {
    const raw = (e.source || 'otro').toLowerCase()
    m.set(raw, (m.get(raw) || 0) + 1)
  }
  return [...m.entries()].map(([fuente, count]) => ({ fuente, count }))
}

export function threatDistributionForChart(events, minTotal = 6) {
  const rows = buildThreatDistribution(events)
  const sum = rows.reduce((s, r) => s + r.count, 0)
  if (sum >= minTotal) return rows
  if (isDevDataEnabled) return MOCK_CHARTS.threat_distribution
  return rows
}

/** Lunes = 0 … Domingo = 6 */
export function buildActivityHeatmap(events) {
  const keyCount = new Map()
  for (const e of events || []) {
    try {
      const d = new Date(e.timestamp)
      const day = (d.getDay() + 6) % 7
      const hour = d.getHours()
      const k = `${day}-${hour}`
      keyCount.set(k, (keyCount.get(k) || 0) + 1)
    } catch {
      /* ignore */
    }
  }
  const out = []
  for (const [k, count] of keyCount) {
    const [day, hour] = k.split('-').map(Number)
    out.push({ day, hour, count })
  }
  return out
}

export function activityHeatmapForChart(events, minCells = 12) {
  const fromEvents = buildActivityHeatmap(events)
  const active = fromEvents.filter((c) => c.count > 0).length
  if (active >= minCells) return fromEvents
  if (isDevDataEnabled) return MOCK_CHARTS.activity_heatmap
  return fromEvents
}

/** Convierte historial legacy { val } a puntos sparkline. */
export function sparklineFromScoreHistory(history, baseScore = 0) {
  if (!Array.isArray(history) || history.length === 0) return null
  return history.map((pt, i) => ({
    timestamp: new Date(Date.now() - (history.length - 1 - i) * 3600000).toISOString(),
    score: Math.min(100, Math.max(0, Number(pt.val ?? pt.score ?? baseScore) || 0)),
  }))
}
