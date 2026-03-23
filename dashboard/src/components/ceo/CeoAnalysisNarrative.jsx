import styles from './CeoAnalysisNarrative.module.css'

export default function CeoAnalysisNarrative({ paragraphs = [] }) {
  const list = Array.isArray(paragraphs) ? paragraphs : []
  if (list.length === 0) return null
  return (
    <section aria-labelledby="ceo-narrative-label">
      <h3 id="ceo-narrative-label" className={styles.sectionLabel}>
        Análisis
      </h3>
      <div className={styles.body}>
        {list.map((p, i) => (
          <p key={i} className={styles.para}>
            {p}
          </p>
        ))}
      </div>
    </section>
  )
}
