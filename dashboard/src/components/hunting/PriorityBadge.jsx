import styles from './PriorityBadge.module.css'

export function PriorityBadge({ value }) {
  const n = Math.min(5, Math.max(1, Number(value) || 3))
  return (
    <div className={styles.wrap} title={`Prioridad ${n}/5`} aria-label={`Prioridad ${n} de 5`}>
      {[1, 2, 3, 4, 5].map((i) => (
        <span key={i} className={i <= n ? styles.dotOn : styles.dotOff} />
      ))}
      <span className={styles.num}>{n}</span>
    </div>
  )
}
