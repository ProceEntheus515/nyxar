import { useMemo } from 'react'
import styles from './CeoHistoryRow.module.css'

function formatShortDate(iso) {
  const d = new Date(iso)
  if (!Number.isFinite(d.getTime())) return '—'
  return d.toLocaleString('es', {
    day: 'numeric',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function firstPreview(paragraphs) {
  const p = Array.isArray(paragraphs) ? paragraphs[0] : ''
  if (!p) return 'Sin texto.'
  const t = p.trim()
  if (t.length <= 96) return t
  return `${t.slice(0, 93)}…`
}

export default function CeoHistoryRow({ analysis, expanded, onToggle }) {
  const preview = useMemo(() => firstPreview(analysis?.paragraphs), [analysis])
  const stamp = formatShortDate(analysis?.created_at)

  return (
    <button type="button" className={styles.row} onClick={onToggle}>
      <span className={styles.chevron} aria-hidden>
        {expanded ? '▼' : '▶'}
      </span>
      <span className={styles.main}>
        <span className={styles.stamp}>[ {stamp} ]</span>
        <span className={styles.preview}>{preview}</span>
      </span>
      {expanded ? (
        <div className={styles.expanded}>
          {(analysis?.paragraphs || []).map((para, i) => (
            <p key={i} className={styles.expandedPara}>
              {para}
            </p>
          ))}
        </div>
      ) : null}
    </button>
  )
}
