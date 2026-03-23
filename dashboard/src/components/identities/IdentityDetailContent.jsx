import { useMemo, useState } from 'react'
import EventCard from '../data/EventCard'
import { areaToColor, scoreToColor } from '../../lib/colors'
import {
  alertsForIdentityHost,
  computeBehaviorSnapshot,
  computeDeviations,
  eventsForIdentityToday,
  habitualHourMask24,
  isIdentityActiveLast30m,
  minutesToClock,
  normalizeBaseline,
} from '../../lib/identityBehavior'
import { useStore } from '../../store'
import styles from './IdentityDetailContent.module.css'

const SEG_N = 16

function initials(nombre) {
  if (!nombre || typeof nombre !== 'string') return '?'
  const parts = nombre.trim().split(/\s+/).filter(Boolean)
  if (parts.length === 0) return '?'
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase()
  return `${parts[0][0]}${parts[parts.length - 1][0]}`.toUpperCase()
}

function deltaLabel(delta) {
  if (delta == null || Number.isNaN(Number(delta))) return null
  const d = Math.round(Number(delta))
  if (d === 0) return null
  if (d > 0) return { text: `↑+${d}`, className: styles.deltaUp }
  return { text: `↓${d}`, className: styles.deltaDown }
}

function segmentClass(score, i, filled) {
  if (i >= filled) return styles.seg
  if (score >= 80) return `${styles.seg} ${styles.segCrit}`
  if (score >= 60) return `${styles.seg} ${styles.segHigh}`
  return `${styles.seg} ${styles.segOn}`
}

/**
 * Perfil completo de identidad en el panel lateral (F08).
 */
export default function IdentityDetailContent({ identityId }) {
  const identities = useStore((s) => s.identities)
  const identityBaselines = useStore((s) => s.identityBaselines)
  const events = useStore((s) => s.events)
  const alerts = useStore((s) => s.alerts)

  const [eventsExpanded, setEventsExpanded] = useState(false)

  const identity = identities?.[String(identityId)]
  const baselineRaw = identityBaselines?.[String(identityId)]
  const baselineNorm = useMemo(() => normalizeBaseline(baselineRaw), [baselineRaw])

  const todayEvents = useMemo(
    () => eventsForIdentityToday(events, identityId),
    [events, identityId],
  )

  const behavior = useMemo(
    () => computeBehaviorSnapshot(todayEvents, baselineNorm),
    [todayEvents, baselineNorm],
  )

  const hostAlerts = useMemo(() => alertsForIdentityHost(alerts, identityId), [alerts, identityId])

  const deviations = useMemo(
    () => computeDeviations(behavior, baselineNorm, hostAlerts),
    [behavior, baselineNorm, hostAlerts],
  )

  const habitualMask = useMemo(
    () => habitualHourMask24(baselineNorm.habitual_start_minutes, baselineNorm.habitual_end_minutes),
    [baselineNorm],
  )

  const lastEvents = useMemo(() => {
    const id = String(identityId || '')
    const list = (events || []).filter((ev) => String(ev?.interno?.ip || '') === id)
    list.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp))
    return list.slice(0, 12)
  }, [events, identityId])

  const visibleEvents = eventsExpanded ? lastEvents : lastEvents.slice(0, 3)

  if (!identity) {
    return <p className={styles.muted}>Identidad no encontrada en el store.</p>
  }

  const area = identity.area || '—'
  const bg = areaToColor(area)
  const score = Math.round(Number(identity.risk_score) || 0)
  const { color, label: bucketLabel } = scoreToColor(score)
  const filledSeg = Math.min(SEG_N, Math.round((score / 100) * SEG_N))
  const active = isIdentityActiveLast30m(identity.last_seen_ts)
  const dLbl = deltaLabel(identity.delta_2h)
  const u = identity.dispositivo || '—'
  const h = identity.hostname || '—'
  const ip = identity.ip_asociada || identity.id || '—'
  const userLine = identity.nombre_completo || '—'

  const baseVol = baselineNorm.baseline_volume_mb
  const todayVol = behavior.volumeTodayMb
  const volPct = baseVol > 0 ? Math.min(100, Math.round((todayVol / baseVol) * 100)) : 0

  return (
    <div className={styles.root}>
      <header className={styles.hero}>
        <div className={styles.heroTop}>
          <div className={styles.avatar} style={{ backgroundColor: bg }} aria-hidden>
            {initials(identity.nombre_completo)}
          </div>
          <div className={styles.heroText}>
            <div className={styles.nameRow}>
              <h3 className={styles.name}>{userLine}</h3>
              <span className={active ? styles.statusLive : styles.statusOff}>
                {active ? 'ACTIVA' : 'INACTIVA'}
              </span>
            </div>
            <p className={styles.meta}>
              {u} · {String(area).toUpperCase()}
              <br />
              {h && h !== u ? `${h} · ${ip}` : ip}
            </p>
          </div>
        </div>

        <div className={styles.riskBlock}>
          <h4 className={styles.sectionTitle}>Riesgo actual</h4>
          <div className={styles.riskRow}>
            <div className={styles.segments} aria-hidden>
              {Array.from({ length: SEG_N }, (_, i) => (
                <span key={i} className={segmentClass(score, i, filledSeg)} />
              ))}
            </div>
            <div className={styles.riskNums}>
              <span className={styles.score} style={{ color }}>
                {score}
              </span>
              <span className={styles.bucket}>{bucketLabel}</span>
              {dLbl ? <span className={dLbl.className}>{dLbl.text}</span> : null}
            </div>
          </div>
        </div>
      </header>

      <section>
        <h4 className={styles.sectionTitle}>Comportamiento</h4>
        <ul className={styles.behaviorList}>
          <li>
            Horario habitual: {minutesToClock(baselineNorm.habitual_start_minutes)} →{' '}
            {minutesToClock(baselineNorm.habitual_end_minutes)}
          </li>
          <li>Hoy activo desde: {behavior.activeSinceLabel}</li>
          <li>
            Dominios habituales: {baselineNorm.known_domains.length} conocidos
            {behavior.newDomains > 0 ? ` · Nuevos hoy: ${behavior.newDomains}` : ''}
          </li>
          <li>
            Volumen hoy: {todayVol}MB / {baseVol}MB base
          </li>
        </ul>
      </section>

      <div className={styles.divider} />

      <section>
        <h4 className={styles.sectionTitle}>Desviaciones detectadas hoy</h4>
        {deviations.length === 0 ? (
          <p className={styles.muted}>Sin desviaciones respecto al baseline en la ventana de hoy.</p>
        ) : (
          <ul className={styles.devList}>
            {deviations.map((d) => (
              <li key={d.id} className={styles.devItem}>
                <span className={d.triggeredAlert ? styles.devIconAlert : styles.devIcon} aria-hidden>
                  {d.triggeredAlert ? '⊘' : '⚠'}
                </span>
                <span>{d.text}</span>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className={styles.vizBlock}>
        <h4 className={styles.sectionTitle}>Línea base visual</h4>
        <div className={styles.vizRow}>
          <span className={styles.vizLabel}>Horario</span>
          <div className={styles.hourStrip} title="Gris: franja habitual · Cian: actividad hoy">
            {habitualMask.map((hab, h) => {
              const tdy = behavior.activeHoursToday[h]
              let cls = styles.hourCell
              if (hab && tdy) cls = `${styles.hourCell} ${styles.hourBoth}`
              else if (tdy) cls = `${styles.hourCell} ${styles.hourToday}`
              else if (hab) cls = `${styles.hourCell} ${styles.hourHabitual}`
              return <span key={h} className={cls} />
            })}
          </div>
        </div>
        <div className={styles.vizRow}>
          <span className={styles.vizLabel}>Volumen</span>
          <div className={styles.volTrack}>
            <div className={styles.volBase} style={{ width: '100%' }} />
            <div className={styles.volToday} style={{ width: `${volPct}%` }} />
          </div>
          <span className={styles.volLegend}>
            base: {baseVol}MB | hoy: {todayVol}MB
          </span>
        </div>
        <p className={styles.volLegend}>
          Dominios: conocidos {baselineNorm.known_domains.length} · nuevos hoy {behavior.newDomains}
        </p>
      </section>

      <section>
        <div className={styles.eventsHead}>
          <h4 className={styles.sectionTitle} style={{ margin: 0 }}>
            Últimos eventos
          </h4>
          {lastEvents.length > 3 ? (
            <button
              type="button"
              className={styles.expandBtn}
              onClick={() => setEventsExpanded((v) => !v)}
              aria-expanded={eventsExpanded}
            >
              {eventsExpanded ? '−' : '+'}
            </button>
          ) : null}
        </div>
        <div className={styles.eventStack}>
          {visibleEvents.length === 0 ? (
            <p className={styles.muted}>Sin eventos recientes para esta identidad.</p>
          ) : (
            visibleEvents.map((ev) => (
              <EventCard key={ev.id} event={ev} compact dense />
            ))
          )}
        </div>
      </section>
    </div>
  )
}
