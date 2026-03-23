/**
 * Cálculo en cliente: comportamiento actual vs baseline (Zustand) y desviaciones.
 * Sin fetch por identidad al abrir el panel.
 */

function startOfLocalDayMs(t = Date.now()) {
  const d = new Date(t)
  d.setHours(0, 0, 0, 0)
  return d.getTime()
}

function endOfLocalDayMs(t = Date.now()) {
  const d = new Date(t)
  d.setHours(23, 59, 59, 999)
  return d.getTime()
}

export function minutesToClock(mins) {
  const h = Math.floor(mins / 60)
  const m = mins % 60
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`
}

function hourOverlapsHabitual(hourIndex, startMin, endMin) {
  const blockStart = hourIndex * 60
  const blockEnd = blockStart + 60
  return Math.max(blockStart, startMin) < Math.min(blockEnd, endMin)
}

/**
 * @param {number} startMin
 * @param {number} endMin
 * @returns {boolean[]}
 */
export function habitualHourMask24(startMin, endMin) {
  return Array.from({ length: 24 }, (_, h) => hourOverlapsHabitual(h, startMin, endMin))
}

function normalizeDomainHost(val) {
  const s = String(val || '')
    .trim()
    .toLowerCase()
  if (!s || /^(\d{1,3}\.){3}\d{1,3}$/.test(s)) return null
  let h = s.replace(/^https?:\/\//, '').split('/')[0].split(':')[0]
  if (h.startsWith('www.')) h = h.slice(4)
  return h || null
}

function domainIsKnown(host, knownList) {
  if (!host) return true
  const h = host.toLowerCase()
  for (const k of knownList || []) {
    const kk = String(k).toLowerCase()
    if (!kk) continue
    if (h === kk || h.endsWith(`.${kk}`)) return true
  }
  return false
}

function identityIp(ev) {
  return String(ev?.interno?.ip || ev?.interno?.id_usuario || '').trim()
}

/**
 * @param {object[]} events
 * @param {string} identityId
 * @returns {object[]}
 */
export function eventsForIdentityToday(events, identityId) {
  const id = String(identityId || '')
  const lo = startOfLocalDayMs()
  const hi = endOfLocalDayMs()
  const out = []
  for (const ev of events || []) {
    if (identityIp(ev) !== id) continue
    const t = new Date(ev.timestamp).getTime()
    if (!Number.isFinite(t) || t < lo || t > hi) continue
    out.push(ev)
  }
  return out
}

/**
 * @param {object} baseline
 * @returns {{ habitual_start_minutes: number, habitual_end_minutes: number, baseline_volume_mb: number, known_domains: string[] }}
 */
export function normalizeBaseline(baseline) {
  const b = baseline || {}
  return {
    habitual_start_minutes: Number(b.habitual_start_minutes) || 8 * 60 + 30,
    habitual_end_minutes: Number(b.habitual_end_minutes) || 18 * 60,
    baseline_volume_mb: Number(b.baseline_volume_mb) || 80,
    known_domains: Array.isArray(b.known_domains) ? b.known_domains.map(String) : [],
  }
}

/**
 * @param {object[]} todayEvents
 * @param {object} baselineNorm
 */
export function computeBehaviorSnapshot(todayEvents, baselineNorm) {
  const { habitual_start_minutes: hs, habitual_end_minutes: he, baseline_volume_mb: baseVol, known_domains } =
    baselineNorm

  const activeHoursToday = Array(24).fill(false)
  let minTs = null
  for (const ev of todayEvents) {
    const t = new Date(ev.timestamp).getTime()
    if (!Number.isFinite(t)) continue
    if (minTs == null || t < minTs) minTs = t
    const d = new Date(t)
    activeHoursToday[d.getHours()] = true
  }

  const domainSet = new Set()
  for (const ev of todayEvents) {
    const host = normalizeDomainHost(ev?.externo?.valor)
    if (host) domainSet.add(host)
  }

  let newDomains = 0
  for (const h of domainSet) {
    if (!domainIsKnown(h, known_domains)) newDomains += 1
  }

  const volFactor = 0.88 + Math.min(0.45, todayEvents.length * 0.012 + newDomains * 0.035)
  const volumeTodayMb = Math.round(baseVol * volFactor)

  let offHours = false
  for (const ev of todayEvents) {
    const t = new Date(ev.timestamp).getTime()
    if (!Number.isFinite(t)) continue
    const mins = new Date(t).getHours() * 60 + new Date(t).getMinutes()
    if (mins < hs || mins > he) {
      offHours = true
      break
    }
  }

  const activeSinceLabel =
    minTs != null
      ? new Date(minTs).toLocaleTimeString('es', { hour: '2-digit', minute: '2-digit' })
      : '—'

  return {
    activeHoursToday,
    activeSinceLabel,
    uniqueDomainsToday: domainSet.size,
    newDomains,
    volumeTodayMb,
    offHoursActivity: offHours,
    eventCountToday: todayEvents.length,
  }
}

/**
 * @param {object} behavior
 * @param {object} baselineNorm
 * @param {object[]} alertsForHost
 * @returns {{ id: string, severity: number, text: string, triggeredAlert: boolean }[]}
 */
export function computeDeviations(behavior, baselineNorm, alertsForHost) {
  const { newDomains, volumeTodayMb, offHoursActivity } = behavior
  const baseVol = baselineNorm.baseline_volume_mb || 1
  const volRatio = volumeTodayMb / baseVol

  const hasStrongAlert = (alertsForHost || []).some((a) => {
    const s = String(a.severidad || '').toLowerCase()
    return s.includes('crit') || s.includes('alta')
  })

  const out = []

  if ((baselineNorm.known_domains || []).length > 0 && newDomains >= 3) {
    out.push({
      id: 'new-domains',
      severity: 72 + Math.min(20, newDomains * 2),
      text: `Visitó ${newDomains} sitios que no están en su historial habitual`,
      triggeredAlert: hasStrongAlert,
    })
  } else if ((baselineNorm.known_domains || []).length > 0 && newDomains >= 1) {
    out.push({
      id: 'new-domains-low',
      severity: 38 + newDomains * 8,
      text:
        newDomains === 1
          ? 'Consultó un dominio nuevo respecto a su línea base habitual'
          : `Consultó ${newDomains} dominios nuevos respecto a su línea base habitual`,
      triggeredAlert: hasStrongAlert,
    })
  }

  if (volRatio >= 1.1) {
    const pct = Math.round((volRatio - 1) * 100)
    out.push({
      id: 'volume',
      severity: 55 + Math.min(25, pct),
      text: `El tráfico de hoy supera en ${pct}% su volumen habitual de referencia`,
      triggeredAlert: hasStrongAlert && volRatio >= 1.15,
    })
  }

  if (offHoursActivity) {
    out.push({
      id: 'off-hours',
      severity: 48,
      text: 'Registró actividad fuera de su franja horaria habitual',
      triggeredAlert: false,
    })
  }

  out.sort((a, b) => b.severity - a.severity)
  return out
}

export function alertsForIdentityHost(alerts, identityId) {
  const id = String(identityId || '')
  return (alerts || []).filter((a) => String(a.host_afectado || '') === id)
}

/** Actividad en los últimos `windowMin` minutos (misma heurística que listas). */
export function isIdentityActiveLast30m(lastSeenISO, windowMin = 30) {
  if (!lastSeenISO) return false
  const diffMin = (Date.now() - new Date(lastSeenISO).getTime()) / 60000
  return diffMin < windowMin
}
