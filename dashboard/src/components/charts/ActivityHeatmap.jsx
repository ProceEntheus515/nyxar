import { Fragment, useMemo } from 'react'
import styles from './ActivityHeatmap.module.css'

const DAYS = ['Lu', 'Ma', 'Mi', 'Ju', 'Vi', 'Sa', 'Do']
const HOURS = Array.from({ length: 24 }, (_, i) => i)

function buildMatrix(data) {
  const m = new Map()
  let max = 0
  ;(Array.isArray(data) ? data : []).forEach((d) => {
    const day = Number(d.day)
    const hour = Number(d.hour)
    if (day < 0 || day > 6 || hour < 0 || hour > 23) return
    const c = Math.max(0, Number(d.count) || 0)
    m.set(`${day}-${hour}`, c)
    if (c > max) max = c
  })
  return { m, max }
}

function cellBackground(count, max) {
  if (count <= 0 || max <= 0) return 'var(--base-surface)'
  const t = count / max
  const pct = Math.round(t * 100)
  return `color-mix(in srgb, var(--base-surface) ${100 - pct}%, var(--cyan-bright))`
}

/**
 * Heatmap 7×24 de actividad (F09).
 */
export default function ActivityHeatmap({ data = [], className = '' }) {
  const { m: matrix, max } = useMemo(() => buildMatrix(data), [data])

  return (
    <div className={`${styles.root} ${className}`.trim()}>
      <div className={styles.grid} role="grid" aria-label="Actividad por día y hora">
        <div className={styles.corner} />
        {HOURS.map((h) => (
          <div key={`xh-${h}`} className={styles.xHead} style={{ gridColumn: h + 2, gridRow: 1 }}>
            {[0, 6, 12, 18].includes(h) ? String(h) : ''}
          </div>
        ))}
        {DAYS.map((label, di) => (
          <Fragment key={label}>
            <div className={styles.yHead} style={{ gridColumn: 1, gridRow: di + 2 }}>
              {label}
            </div>
            {HOURS.map((h) => {
              const c = matrix.get(`${di}-${h}`) ?? 0
              return (
                <button
                  type="button"
                  key={`${di}-${h}`}
                  className={styles.cell}
                  style={{ background: cellBackground(c, max), gridColumn: h + 2, gridRow: di + 2 }}
                  title={`${c} eventos · ${label} ${h}:00`}
                  aria-label={`${c} eventos el ${label} a las ${h} horas`}
                />
              )
            })}
          </Fragment>
        ))}
      </div>
    </div>
  )
}
