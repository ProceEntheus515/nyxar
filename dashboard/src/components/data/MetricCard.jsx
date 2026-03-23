import { useRef } from 'react'
import { useDataFlip } from '../../hooks/useAnimation'
import styles from './MetricCard.module.css'

function formatValue(value, unit) {
  if (value == null) return '—'
  if (typeof value === 'number' && Number.isFinite(value)) {
    const s = value.toLocaleString('es')
    return unit ? `${s}${unit}` : s
  }
  return String(value)
}

/**
 * Métrica compacta para cabeceras de vista (F08).
 */
export default function MetricCard({
  label,
  value,
  delta,
  unit = '',
  trend = false,
  className = '',
}) {
  const numValue = typeof value === 'number' ? value : Number(value)
  const coerced = Number.isFinite(numValue) ? numValue : value
  const ref = useRef(null)
  useDataFlip(typeof coerced === 'number' ? coerced : 0, ref)

  const deltaNum = delta != null ? Number(delta) : null
  const hasDelta = deltaNum != null && !Number.isNaN(deltaNum)
  const positive = hasDelta && deltaNum > 0
  const negative = hasDelta && deltaNum < 0

  return (
    <div className={`${styles.card} ${className}`.trim()}>
      <div className={styles.label}>{label}</div>
      <div className={styles.valueBlock}>
        <span ref={ref} className={styles.value} data-value={coerced}>
          {formatValue(coerced, unit)}
        </span>
        {hasDelta ? (
          <span
            className={`${styles.delta} ${positive ? styles.deltaUp : negative ? styles.deltaDown : ''}`}
          >
            {positive ? '+' : ''}
            {deltaNum.toLocaleString('es')}
            {trend ? (positive ? ' ↑' : negative ? ' ↓' : '') : ''}
          </span>
        ) : null}
      </div>
    </div>
  )
}
