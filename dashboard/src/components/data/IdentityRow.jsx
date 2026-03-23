import { areaToColor, scoreToColor } from '../../lib/colors'
import { scoreToSeverity } from '../../lib/utils'
import RiskBadge from '../ui/RiskBadge'
import styles from './IdentityRow.module.css'

function initials(nombre) {
  if (!nombre || typeof nombre !== 'string') return '?'
  const parts = nombre.trim().split(/\s+/).filter(Boolean)
  if (parts.length === 0) return '?'
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase()
  return `${parts[0][0]}${parts[parts.length - 1][0]}`.toUpperCase()
}

/** Activo si última actividad en los últimos 30 min (misma heurística que la vista previa). */
function isActiveNow(lastSeenISO) {
  if (!lastSeenISO) return false
  const diffMin = (Date.now() - new Date(lastSeenISO).getTime()) / 60000
  return diffMin < 30
}

function trendArrow(delta) {
  if (delta == null || Number.isNaN(Number(delta))) return null
  const d = Number(delta)
  if (d > 0) return { char: '▲', className: styles.trendUp }
  if (d < 0) return { char: '▼', className: styles.trendDown }
  return null
}

/**
 * Fila de identidad para listas densas (F08).
 */
export default function IdentityRow({
  identity,
  onClick,
  compact = false,
  selected = false,
  className = '',
}) {
  if (!identity) return null

  const area = identity.area || '—'
  const bg = areaToColor(area)
  const ini = initials(identity.nombre_completo)
  const active = isActiveNow(identity.last_seen_ts)
  const score = Number(identity.risk_score) || 0
  const bucket = scoreToColor(score)
  const delta = identity.delta_2h
  const trend = trendArrow(delta)
  const privileged = Boolean(identity.es_privilegiado)

  const u = identity.dispositivo || identity.hostname || '—'
  const h = identity.hostname && identity.dispositivo !== identity.hostname ? identity.hostname : ''
  const subline = compact && !h ? u : h ? `${u}  ·  ${h}` : u

  return (
    <div
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
      onClick={onClick}
      onKeyDown={
        onClick
          ? (ev) => {
              if (ev.key === 'Enter' || ev.key === ' ') {
                ev.preventDefault()
                onClick()
              }
            }
          : undefined
      }
      className={`${styles.row} ${compact ? styles.compact : ''} ${selected ? styles.selected : ''} ${className}`.trim()}
    >
      <div className={styles.avatar} style={{ backgroundColor: bg }} aria-hidden>
        {ini}
      </div>

      <div className={styles.main}>
        <div className={styles.nameLine}>
          <span className={styles.name}>{identity.nombre_completo || 'Sin nombre'}</span>
          {privileged ? (
            <span className={styles.priv} aria-label="Cuenta privilegiada" title="Privilegiado">
              ◆
            </span>
          ) : null}
        </div>
        <div className={styles.sub}>{subline}</div>
      </div>

      <div className={styles.activity} aria-label={active ? 'Activo' : 'Inactivo'}>
        <span
          className={`${styles.activityDot} ${active ? `${styles.activityLive} animate-live` : styles.activityOff}`}
        />
      </div>

      <div className={styles.area}>{area}</div>

      <div className={styles.risk}>
        <div className={styles.riskTop}>
          <span className={styles.riskNum} style={{ color: bucket.color }}>
            {Math.round(score)}
          </span>
          {trend ? (
            <span className={trend.className} aria-hidden>
              {trend.char}
            </span>
          ) : null}
        </div>
        <RiskBadge score={score} severidad={scoreToSeverity(score)} />
      </div>
    </div>
  )
}
