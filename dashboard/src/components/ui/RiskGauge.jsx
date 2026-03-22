import { useRef } from 'react'
import { scoreToColor } from '../../lib/colors'
import { useDataFlip } from '../../hooks/useAnimation'
import styles from './RiskGauge.module.css'

/**
 * Métrica de riesgo 0–100 con barra vertical y etiqueta de bucket (F07).
 */
export default function RiskGauge({ score, size = 'md', showLabel = true, className = '' }) {
  const n = Math.min(100, Math.max(0, Number(score) || 0))
  const { color, label } = scoreToColor(n)
  const numberRef = useRef(null)
  useDataFlip(n, numberRef)

  const sz = size === 'sm' || size === 'lg' ? size : 'md'

  return (
    <div
      className={`${styles.wrap} ${styles[`size${sz.charAt(0).toUpperCase()}${sz.slice(1)}`]} ${className}`.trim()}
      aria-label={`Riesgo ${n}, ${label}`}
    >
      <span className={styles.bar} style={{ backgroundColor: color }} aria-hidden />
      <div className={styles.body}>
        <span
          ref={numberRef}
          className={`${styles.value} ${n > 80 ? 'animate-critical' : ''}`}
          style={{ color }}
        >
          {n}
        </span>
        {showLabel ? <span className={styles.caption}>{label}</span> : null}
      </div>
    </div>
  )
}
