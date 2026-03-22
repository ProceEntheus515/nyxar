import StatusDot from '../ui/StatusDot'
import styles from './HealthCard.module.css'

function mapEstadoToDot(estado) {
  if (estado === 'ok') return 'online'
  if (estado === 'warning') return 'warning'
  if (estado === 'critical') return 'critical'
  return 'unknown'
}

function formatCheckedAt(iso) {
  if (!iso) return ''
  try {
    const d = new Date(iso)
    return d.toLocaleString()
  } catch {
    return String(iso)
  }
}

export default function HealthCard({ titulo, health }) {
  if (!health) return null
  const dot = mapEstadoToDot(health.estado)
  const lat =
    health.latencia_ms != null && health.latencia_ms !== undefined
      ? `${Number(health.latencia_ms).toFixed(1)} ms`
      : null
  const detKeys = health.detalles && typeof health.detalles === 'object'
  const detStr = detKeys
    ? Object.entries(health.detalles)
        .map(([k, v]) => `${k}: ${v}`)
        .join('\n')
    : ''

  return (
    <article className={styles.card}>
      <div className={styles.header}>
        <h3 className={styles.title}>{titulo || health.nombre}</h3>
        <StatusDot status={dot} size="lg" />
      </div>
      <p className={styles.message}>{health.mensaje}</p>
      <div className={styles.meta}>
        {lat && <span>Latencia {lat}</span>}
        {lat && <span> · </span>}
        <span>{formatCheckedAt(health.checked_at)}</span>
      </div>
      {detStr ? <pre className={styles.details}>{detStr}</pre> : null}
    </article>
  )
}
