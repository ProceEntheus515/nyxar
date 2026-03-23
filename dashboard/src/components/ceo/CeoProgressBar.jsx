import styles from './CeoProgressBar.module.css'

export default function CeoProgressBar({ value, className = '' }) {
  const pct = Math.max(0, Math.min(100, Number(value) || 0))
  return (
    <div
      className={`${styles.track} ${className}`.trim()}
      role="progressbar"
      aria-valuenow={Math.round(pct)}
      aria-valuemin={0}
      aria-valuemax={100}
    >
      <div className={styles.fill} style={{ width: `${pct}%` }} />
    </div>
  )
}
