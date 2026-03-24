import { useMemo } from 'react'
import { useStore } from '../store'
import AiMemoCard from './ai/AiMemoCard'
import styles from './AiMemo.module.css'

function memoText(m) {
  const c = m?.contenido
  if (typeof c === 'string' && c.trim()) return c.trim()
  return ''
}

function normalizePrioridad(raw) {
  const p = String(raw || '')
    .toLowerCase()
    .normalize('NFD')
    .replace(/\p{M}/gu, '')
  if (p.includes('crit')) return 'critica'
  if (p === 'alta') return 'alta'
  if (p === 'media') return 'media'
  if (p === 'info' || p === 'ninguna') return 'info'
  return 'info'
}

/**
 * Últimos memos del analista IA (I09): lectura desde Zustand, máximo 5 visibles.
 */
export default function AiMemo({ collapsed = false }) {
  const aiMemos = useStore((s) => s.aiMemos)

  const visible = useMemo(() => (Array.isArray(aiMemos) ? aiMemos.slice(0, 5) : []), [aiMemos])

  if (!visible.length) {
    if (collapsed) return null
    return (
      <section className={styles.wrap} aria-label="Análisis IA">
        <h2 className={styles.heading}>IA</h2>
        <p className={styles.empty}>Sin memos recientes.</p>
      </section>
    )
  }

  if (collapsed) {
    const top = visible[0]
    const p = normalizePrioridad(top?.prioridad)
    return (
      <section className={styles.wrapCollapsed} aria-label="Último memo IA" title={memoText(top)}>
        <span className={styles.collapsedDot} data-sev={p} aria-hidden />
      </section>
    )
  }

  return (
    <section className={styles.wrap} aria-label="Análisis IA">
      <h2 className={styles.heading}>IA</h2>
      <ul className={styles.list}>
        {visible.map((m) => (
          <AiMemoCard key={m.id || `${m.created_at}-${memoText(m).slice(0, 12)}`} memo={m} />
        ))}
      </ul>
    </section>
  )
}
