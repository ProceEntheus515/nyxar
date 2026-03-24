import Badge from '../ui/Badge'
import TimeAgo from '../ui/TimeAgo'
import styles from './AiMemoCard.module.css'

function normalizePrioridad(raw) {
  const p = String(raw || '')
    .toLowerCase()
    .normalize('NFD')
    .replace(/\p{M}/gu, '')
  if (p.includes('crit')) return 'critica'
  if (p === 'alta') return 'alta'
  if (p === 'media') return 'media'
  return 'info'
}

function badgeVariantForPrioridad(p) {
  if (p === 'critica') return 'critical'
  if (p === 'alta') return 'high'
  if (p === 'media') return 'medium'
  return 'info'
}

function memoText(m) {
  const c = m?.contenido
  if (typeof c === 'string' && c.trim()) return c.trim()
  return ''
}

export default function AiMemoCard({ memo }) {
  const p = normalizePrioridad(memo?.prioridad)
  const text = memoText(memo)
  const ts = memo?.created_at || memo?.timestamp

  return (
    <li
      className={`${styles.item} ${p === 'critica' ? styles.itemCritical : ''}`.trim()}
    >
      <div className={styles.row}>
        <Badge variant={badgeVariantForPrioridad(p)} size="sm">
          {p}
        </Badge>
        {ts ? <TimeAgo timestamp={ts} className={styles.when} /> : null}
      </div>
      {memo?.titulo ? <p className={styles.title}>{memo.titulo}</p> : null}
      {text ? <p className={styles.body}>{text}</p> : null}
    </li>
  )
}
