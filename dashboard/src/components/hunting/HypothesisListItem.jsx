import { PriorityBadge } from './PriorityBadge'
import styles from './HypothesisListItem.module.css'

function formatTs(iso) {
  if (!iso) return '—'
  try {
    const d = new Date(iso)
    return Number.isNaN(d.getTime()) ? String(iso) : d.toLocaleString()
  } catch {
    return String(iso)
  }
}

export function HypothesisListItem({
  hypothesis,
  selected,
  onSelect,
  onInvestigate,
  investigating,
  disabledInvestigate,
}) {
  const h = hypothesis
  const estado = h.estado || 'nueva'
  const isStruck = estado === 'descartada'
  const isConfirmed = estado === 'confirmada'

  return (
    <article
      className={`${styles.card} ${selected ? styles.cardSelected : ''} ${isStruck ? styles.cardStruck : ''}`}
      aria-current={selected ? 'true' : undefined}
    >
      <button type="button" className={styles.mainHit} onClick={() => onSelect(h)} aria-label={`Ver ${h.titulo}`}>
        <div className={styles.rowTop}>
          <PriorityBadge value={h.prioridad} />
          {h.tecnica_mitre && h.tecnica_mitre !== 'T0000' && (
            <span className={styles.mitre}>{h.tecnica_mitre}</span>
          )}
        </div>
        <h3 className={styles.title}>{h.titulo}</h3>
        <div className={styles.meta}>
          <span className={styles.estado} data-estado={estado}>
            {estado}
          </span>
          {isConfirmed && <span className={styles.badgeThreat}>AMENAZA CONFIRMADA</span>}
        </div>
        <time className={styles.time} dateTime={h.creada_at}>
          {formatTs(h.creada_at)}
        </time>
      </button>
      {estado === 'nueva' && (
        <div className={styles.actions}>
          <button
            type="button"
            className={styles.btnRun}
            onClick={(e) => {
              e.stopPropagation()
              onInvestigate(h)
            }}
            disabled={disabledInvestigate || investigating}
          >
            {investigating ? 'Ejecutando…' : 'Investigar'}
          </button>
        </div>
      )}
    </article>
  )
}
