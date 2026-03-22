import styles from './EmptyState.module.css'

/**
 * Vacío sin ilustración genérica: glifo Unicode + texto (F07).
 */
export default function EmptyState({ icon, title, description, action, className = '' }) {
  return (
    <div className={`${styles.wrap} ${className}`.trim()} role="status">
      <div className={styles.glyph} aria-hidden>
        {icon}
      </div>
      <h3 className={styles.title}>{title}</h3>
      <p className={styles.desc}>{description}</p>
      {action ? <div className={styles.action}>{action}</div> : null}
    </div>
  )
}
