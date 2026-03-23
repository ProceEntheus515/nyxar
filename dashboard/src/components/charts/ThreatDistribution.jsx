import { useMemo } from 'react'
import { normalizeSourceKey, SOURCE_COLORS } from '../../lib/colors'
import styles from './ThreatDistribution.module.css'

function colorForRow(row) {
  if (row.color) return row.color
  const key = normalizeSourceKey(row.fuente)
  if (key && SOURCE_COLORS[key]) return SOURCE_COLORS[key].color
  return 'var(--base-muted)'
}

/**
 * Barras horizontales por fuente (F09). Sin pie chart.
 */
export default function ThreatDistribution({ data = [], className = '' }) {
  const total = useMemo(
    () => (Array.isArray(data) ? data : []).reduce((s, d) => s + (Number(d.count) || 0), 0),
    [data],
  )

  const rows = useMemo(() => {
    const list = Array.isArray(data) ? [...data] : []
    return list
      .sort((a, b) => (Number(b.count) || 0) - (Number(a.count) || 0))
      .map((d) => {
        const c = Number(d.count) || 0
        const pct = total > 0 ? Math.round((c / total) * 100) : 0
        return {
          fuente: String(d.fuente || '—').toUpperCase(),
          count: c,
          pct,
          color: colorForRow({ ...d, fuente: d.fuente }),
        }
      })
  }, [data, total])

  return (
    <div className={`${styles.wrap} ${className}`.trim()} role="list">
      {rows.map((row, i) => (
        <div key={row.fuente + i} className={styles.row} role="listitem">
          <span className={styles.label}>{row.fuente}</span>
          <div className={styles.barTrack}>
            <div
              className={styles.barFill}
              style={{
                width: `${row.pct}%`,
                backgroundColor: row.color,
                animationDelay: `${i * 60}ms`,
              }}
            />
          </div>
          <span className={styles.count}>{row.count.toLocaleString('es')}</span>
          <span className={styles.pct}>({row.pct}%)</span>
        </div>
      ))}
    </div>
  )
}
