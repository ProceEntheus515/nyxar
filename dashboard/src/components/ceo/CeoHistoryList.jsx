import CeoHistoryRow from './CeoHistoryRow'
import styles from './CeoHistoryList.module.css'

export default function CeoHistoryList({ analyses, expandedId, onExpand }) {
  if (!Array.isArray(analyses) || analyses.length === 0) return null
  return (
    <section aria-labelledby="ceo-history-title">
      <h3 id="ceo-history-title" className={styles.title}>
        Historial
      </h3>
      <ul className={styles.list}>
        {analyses.map((a) => (
          <li key={a.id} className={styles.item}>
            <CeoHistoryRow
              analysis={a}
              expanded={expandedId === a.id}
              onToggle={() => onExpand(expandedId === a.id ? null : a.id)}
            />
          </li>
        ))}
      </ul>
    </section>
  )
}
