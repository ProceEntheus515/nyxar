import styles from './SidebarHealthDot.module.css'

/**
 * Punto de salud agregada (F06): nominal / warning / crítico o WS caído.
 * animate-live / animate-critical vienen de motion.css (keyframes globales).
 */
export default function SidebarHealthDot({ variant }) {
  if (variant === 'critical') {
    return (
      <span
        className={`${styles.dot} ${styles.dotCritical} animate-critical`}
        aria-hidden
      />
    )
  }
  if (variant === 'warning') {
    return <span className={`${styles.dot} ${styles.dotWarning}`} aria-hidden />
  }
  return (
    <span
      className={`${styles.dot} ${styles.dotNominal} animate-live`}
      aria-hidden
    />
  )
}
