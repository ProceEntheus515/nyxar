import { useRef, useEffect, useState, useMemo } from 'react'
import { useStore } from '../../store'
import { useDataFlip } from '../../hooks/useAnimation'
import { RISK_COLORS } from '../../lib/utils'
import styles from './StatusBar.module.css'

const SEVERITY_RANK = { critica: 5, alta: 4, media: 3, baja: 2, info: 1 }

function normalizeSeveridadKey(raw) {
  const t = String(raw || '')
    .toLowerCase()
    .normalize('NFD')
    .replace(/\p{M}/gu, '')
  if (t.includes('crit')) return 'critica'
  if (t === 'alta') return 'alta'
  if (t === 'media') return 'media'
  if (t === 'baja') return 'baja'
  return 'info'
}

function highestOpenIncidentSeverity(incidents) {
  let best = 'info'
  let rank = 0
  for (const inc of incidents || []) {
    if (String(inc.estado || '').toLowerCase() === 'cerrado') continue
    const key = normalizeSeveridadKey(inc.severidad)
    const r = SEVERITY_RANK[key] || 0
    if (r > rank) {
      rank = r
      best = key
    }
  }
  return best
}

export default function StatusBar() {
  const { stats, incidents, wsConnected, wsEverConnected } = useStore()
  const eventosRef = useRef(null)
  const eventosPorMin = stats?.eventos_por_min ?? 0

  useDataFlip(eventosPorMin, eventosRef)

  const [clock, setClock] = useState(() => new Date())

  useEffect(() => {
    const id = window.setInterval(() => setClock(new Date()), 1000)
    return () => window.clearInterval(id)
  }, [])

  const alertasAbiertas = stats?.alertas_abiertas ?? 0

  const alertColor = useMemo(() => {
    if (!alertasAbiertas) return 'var(--base-subtle)'
    const key = highestOpenIncidentSeverity(incidents)
    const cfg = RISK_COLORS[key] || RISK_COLORS.info
    return cfg.text
  }, [alertasAbiertas, incidents])

  const clockStr = useMemo(
    () =>
      clock.toLocaleString(undefined, {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        day: '2-digit',
        month: 'short',
      }),
    [clock]
  )

  return (
    <header className={styles.bar} role="banner">
      <div className={styles.metrics}>
        <div className={styles.liveBlock}>
          <span
            className={`${styles.liveDot} ${wsConnected ? 'animate-live' : styles.liveDotMuted}`}
            aria-hidden
          />
          {wsConnected ? (
            <span className={styles.liveLabel}>LIVE</span>
          ) : wsEverConnected ? (
            <span className={styles.reconnectLabel}>RECONECTANDO</span>
          ) : (
            <span className={styles.reconnectLabel}>CONECTANDO</span>
          )}
        </div>

        <div className={styles.metric}>
          <span className={styles.metricLabel}>Eventos/min</span>
          <span ref={eventosRef} className={styles.metricValue}>
            {eventosPorMin}
          </span>
        </div>

        <div className={styles.metric}>
          <span className={styles.metricLabel}>Alertas abiertas</span>
          <span className={styles.metricValue} style={{ color: alertColor }}>
            {alertasAbiertas}
          </span>
        </div>
      </div>

      <time className={styles.clock} dateTime={clock.toISOString()}>
        {clockStr}
      </time>
    </header>
  )
}
