import SourceTag from '../ui/SourceTag'
import TimeAgo from '../ui/TimeAgo'
import DataChip from '../ui/DataChip'
import AreaBadge from '../ui/AreaBadge'
import Badge from '../ui/Badge'
import { normalizeSourceKey, SOURCE_COLORS, scoreToColor } from '../../lib/colors'
import styles from './EventCard.module.css'

function isProbablyIp(s) {
  const v = String(s || '').trim()
  if (!v) return false
  return /^(\d{1,3}\.){3}\d{1,3}$/.test(v)
}

function enrichmentContext(event) {
  const e = event?.enrichment || {}
  const parts = []
  if (e.ip_resuelta) parts.push(e.ip_resuelta)
  if (e.pais || e.country) parts.push(e.pais || e.country)
  if (e.asn || e.as) parts.push(typeof e.as === 'string' ? e.as : e.asn ? `AS${e.asn}` : '')
  return parts.filter(Boolean).join('  ·  ')
}

/**
 * Tarjeta de evento para Timeline (F08).
 */
export default function EventCard({
  event,
  compact = false,
  selected = false,
  onClick,
  className = '',
}) {
  if (!event) return null

  const key = normalizeSourceKey(event.source)
  const sourceColor = key && SOURCE_COLORS[key] ? SOURCE_COLORS[key].color : 'var(--base-border)'
  const risk = Number(event.enrichment?.risk_score)
  const hasRisk = Number.isFinite(risk)
  const borderScoreColor = hasRisk && risk > 60 ? scoreToColor(risk).color : sourceColor

  const ts = event.timestamp
  const isNew = ts && (Date.now() - new Date(ts).getTime()) / 1000 < 30
  const externoVal = event.externo?.valor || '—'
  const chipType = isProbablyIp(externoVal) ? 'ip' : 'domain'
  const userLabel = event.interno?.id_usuario || event.interno?.ip || '—'
  const area = event.interno?.area || 'Desconocido'
  const ctx = enrichmentContext(event)

  const showSuspicious = hasRisk && risk > 50

  return (
    <article
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
      className={[
        styles.card,
        compact ? styles.compact : '',
        selected ? styles.selected : '',
        isNew ? 'animate-fadeUp' : '',
        className,
      ]
        .filter(Boolean)
        .join(' ')}
      style={{ '--event-border-color': borderScoreColor }}
    >
      <div className={styles.header}>
        <SourceTag source={event.source} className={styles.source} />
        <span className={styles.meta}>
          <span className={styles.user}>{userLabel}</span>
          <span className={styles.dot} aria-hidden>
            ·
          </span>
          <AreaBadge area={area} className={styles.areaBadge} />
        </span>
        <TimeAgo timestamp={ts} className={styles.time} />
      </div>

      {!compact ? (
        <>
          <div className={styles.main}>
            <DataChip value={externoVal} type={chipType} truncate={chipType === 'domain'} />
          </div>
          {(ctx || showSuspicious) && (
            <div className={styles.footer}>
              {ctx ? <span className={styles.context}>{ctx}</span> : <span />}
              {showSuspicious ? (
                <Badge variant="high" size="sm" dot>
                  SOSPECHOSO {Math.round(risk)}
                </Badge>
              ) : null}
            </div>
          )}
        </>
      ) : (
        <div className={styles.compactMain}>
          <DataChip value={externoVal} type={chipType} truncate />
        </div>
      )}
    </article>
  )
}
