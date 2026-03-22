import { normalizeSourceKey, SOURCE_COLORS } from '../../lib/colors'
import styles from './SourceTag.module.css'

/**
 * Fuente de evento compacta: glifo + etiqueta (F07).
 */
export default function SourceTag({ source, className = '' }) {
  const key = normalizeSourceKey(source)
  const meta = key ? SOURCE_COLORS[key] : null
  const label = meta?.label ?? String(source || '—').toUpperCase()
  const icon = meta?.icon ?? '◆'
  const color = meta?.color ?? 'var(--base-muted)'

  return (
    <span className={`${styles.tag} ${className}`.trim()}>
      <span className={styles.icon} style={{ color }} aria-hidden>
        {icon}
      </span>
      <span className={styles.label} style={{ color }}>
        {label}
      </span>
    </span>
  )
}
