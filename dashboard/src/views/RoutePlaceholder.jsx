import styles from './RoutePlaceholder.module.css'

/**
 * Vista mínima para rutas aún sin pantalla (F06: Respuestas, Reportes, CEO).
 */
export default function RoutePlaceholder({ title, description }) {
  return (
    <div className={styles.wrap}>
      <h1 className={styles.title}>{title}</h1>
      <p className={styles.desc}>{description}</p>
    </div>
  )
}
