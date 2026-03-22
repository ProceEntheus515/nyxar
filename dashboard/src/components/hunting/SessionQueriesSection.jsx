import { QueryStatusIcon } from './QueryStatusIcon'
import styles from './SessionQueriesSection.module.css'

function queryVariant(q) {
  if (q.error_o_timeout === 'timeout') return 'timeout'
  if (q.ok === false && q.error_o_timeout) return 'timeout'
  return 'ok'
}

export function SessionQueriesSection({ hypothesis, detalleQueries, runningPlaceholder, etaHint }) {
  const qs = hypothesis?.queries_sugeridas || []
  const list = detalleQueries || []

  return (
    <section className={styles.section} aria-labelledby="hunt-queries-title">
      <h2 id="hunt-queries-title" className={styles.heading}>
        Queries ejecutadas
      </h2>
      {etaHint && <p className={styles.eta}>{etaHint}</p>}
      <ul className={styles.list}>
        {runningPlaceholder &&
          (qs.length ? qs : ['Procesando…']).map((desc, i) => (
            <li key={`run-${i}`} className={styles.item}>
              <QueryStatusIcon variant="running" />
              <div className={styles.body}>
                <p className={styles.desc}>{typeof desc === 'string' ? desc : `Consulta ${i + 1}`}</p>
                <p className={styles.status}>Ejecutando en servidor</p>
              </div>
            </li>
          ))}
        {!runningPlaceholder &&
          list.map((q, i) => {
            const variant = queryVariant(q)
            const desc = qs[i] || `Consulta ${i + 1}`
            return (
              <li key={i} className={styles.item}>
                <QueryStatusIcon variant={variant === 'ok' ? 'ok' : variant} />
                <div className={styles.body}>
                  <p className={styles.desc}>{desc}</p>
                  <p className={styles.status}>
                    {variant === 'timeout' ? 'Timeout o error' : 'Completada'} — {q.resultado_count ?? 0}{' '}
                    resultado(s)
                  </p>
                </div>
              </li>
            )
          })}
        {!runningPlaceholder && list.length === 0 && (
          <li className={styles.empty}>No hay queries registradas en esta sesión.</li>
        )}
      </ul>
    </section>
  )
}
