import styles from './CeoRecommendedAction.module.css'

export default function CeoRecommendedAction({ text }) {
  if (!text?.trim()) return null
  return (
    <aside className={styles.card} aria-label="Acción recomendada">
      <p className={styles.title}>Acción recomendada</p>
      <p className={styles.text}>{text.trim()}</p>
    </aside>
  )
}
