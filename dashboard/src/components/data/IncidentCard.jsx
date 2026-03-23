import { useState } from 'react'
import { useStore } from '../../store'
import TimeAgo from '../ui/TimeAgo'
import Badge from '../ui/Badge'
import styles from './IncidentCard.module.css'

function stripeColor(severidad) {
  const s = String(severidad || '')
    .toLowerCase()
    .normalize('NFD')
    .replace(/\p{M}/gu, '')
  if (s.includes('crit')) return 'var(--critical-base)'
  if (s.includes('alt')) return 'var(--high-base)'
  if (s.includes('med')) return 'var(--medium-base)'
  if (s.includes('baj')) return 'var(--clean-muted)'
  return 'var(--info-base)'
}

function badgeVariant(severidad) {
  const s = String(severidad || '').toLowerCase()
  if (s.includes('crit')) return 'critical'
  if (s.includes('alt')) return 'high'
  if (s.includes('med')) return 'medium'
  return 'info'
}

function incidentBody(incident) {
  return (
    incident?.memo_claude ||
    incident?.descripcion_ia ||
    incident?.resumen_ia ||
    incident?.descripcion ||
    'Sin descripción detallada.'
  )
}

function incidentId(incident) {
  return incident?.id ?? incident?.evento_original_id ?? incident?._id ?? null
}

/**
 * Tarjeta de incidente; expansión con grid 0fr→1fr cuando expandable (F08).
 */
export default function IncidentCard({
  incident,
  expanded: expandedProp,
  onToggleExpand,
  expandable = true,
  className = '',
}) {
  const openDetailPanel = useStore((s) => s.openDetailPanel)
  const [localExpanded, setLocalExpanded] = useState(false)

  const controlled =
    typeof expandedProp === 'boolean' && typeof onToggleExpand === 'function'
  const expanded = controlled ? expandedProp : localExpanded
  const toggleExpand = () => {
    if (controlled) onToggleExpand()
    else setLocalExpanded((v) => !v)
  }

  if (!incident) return null

  const sev = incident.severidad || 'INFO'
  const title = incident.patron || incident.titulo || 'Incidente'
  const ts = incident.timestamp
  const host = incident.host_afectado || incident.interno?.hostname || '—'
  const user = incident.interno?.id_usuario || incident.usuario || '—'
  const id = incidentId(incident)
  const body = incidentBody(incident)

  const investigate = (e) => {
    e.stopPropagation()
    if (id != null) openDetailPanel('incident', id)
  }

  return (
    <article
      className={`${styles.card} ${className}`.trim()}
      style={{ '--incident-stripe': stripeColor(sev) }}
    >
      <div className={styles.stripe} aria-hidden />
      <div className={styles.inner}>
        <header className={styles.header}>
          <div className={styles.headerLeft}>
            <Badge variant={badgeVariant(sev)} size="sm" dot>
              {String(sev).toUpperCase()}
            </Badge>
            <h3 className={styles.title}>{title}</h3>
          </div>
          {expandable ? (
            <button
              type="button"
              className={styles.expandBtn}
              onClick={toggleExpand}
              aria-expanded={expanded}
              aria-label={expanded ? 'Contraer detalle' : 'Expandir detalle'}
            >
              {expanded ? '▾' : '▸'}
            </button>
          ) : null}
        </header>
        <div className={styles.subheader}>
          {ts ? <TimeAgo timestamp={ts} className={styles.time} /> : <span className={styles.time}>—</span>}
          <span className={styles.hostLine}>
            <span>{user}</span>
            <span className={styles.sep} aria-hidden>
              ·
            </span>
            <span>{host}</span>
          </span>
        </div>

        {!expandable ? (
          <div className={styles.staticBody}>
            <p className={styles.memoClamp}>{body}</p>
            <div className={styles.actions}>
              <button type="button" className={styles.investigate} onClick={investigate}>
                Investigar
              </button>
            </div>
          </div>
        ) : (
          <div className={`${styles.expandGrid} ${expanded ? styles.expandGridOpen : ''}`}>
            <div className={styles.expandMeasure}>
              <div className={styles.body}>
                <p className={styles.memo}>{body}</p>
                <div className={styles.actions}>
                  <button type="button" className={styles.investigate} onClick={investigate}>
                    Investigar
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </article>
  )
}
