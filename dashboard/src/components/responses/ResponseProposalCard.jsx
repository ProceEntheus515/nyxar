import { useState } from 'react'
import Badge from '../ui/Badge'
import styles from './ResponseProposalCard.module.css'

function urgenciaVariant(u) {
  const s = String(u || '').toLowerCase()
  if (s.includes('inmedi')) return 'critical'
  if (s.includes('hora')) return 'high'
  return 'medium'
}

export default function ResponseProposalCard({ proposal, onApprove, onReject, busyId }) {
  const [comentario, setComentario] = useState('')
  const [motivo, setMotivo] = useState('')
  const pid = proposal?.id
  const plan = proposal?.plan || {}
  const acciones = Array.isArray(plan.acciones) ? plan.acciones : []
  const busy = busyId === pid

  return (
    <article className={styles.card}>
      <header className={styles.head}>
        <div className={styles.ids}>
          <span className={styles.mono}>{pid}</span>
          <span className={styles.sep}>·</span>
          <span className={styles.incident}>incidente {proposal?.incident_id || '—'}</span>
        </div>
        <Badge variant={urgenciaVariant(plan.urgencia)} size="sm">
          {plan.urgencia || 'urgencia'}
        </Badge>
      </header>

      <p className={styles.just}>{plan.justificacion || 'Sin justificación.'}</p>

      {acciones.length > 0 ? (
        <ul className={styles.acciones}>
          {acciones.map((a, i) => (
            <li key={`${pid}-a-${i}`} className={styles.accion}>
              <span className={styles.accionTipo}>{a.tipo || 'acción'}</span>
              <span className={styles.mono}>{a.objetivo || ''}</span>
              {a.descripcion ? (
                <span className={styles.accionDesc}>{a.descripcion}</span>
              ) : null}
            </li>
          ))}
        </ul>
      ) : null}

      <div className={styles.actions}>
        <label className={styles.lbl} htmlFor={`ap-${pid}`}>
          Comentario (aprobación)
        </label>
        <textarea
          id={`ap-${pid}`}
          className={styles.ta}
          rows={2}
          value={comentario}
          onChange={(e) => setComentario(e.target.value)}
          disabled={busy}
        />
        <div className={styles.rowBtns}>
          <button
            type="button"
            className={styles.btnApprove}
            disabled={busy}
            onClick={() => onApprove(pid, comentario)}
          >
            Aprobar y ejecutar
          </button>
        </div>

        <label className={styles.lbl} htmlFor={`rj-${pid}`}>
          Motivo rechazo
        </label>
        <input
          id={`rj-${pid}`}
          className={styles.input}
          type="text"
          value={motivo}
          onChange={(e) => setMotivo(e.target.value)}
          disabled={busy}
          placeholder="Obligatorio para rechazar"
        />
        <button
          type="button"
          className={styles.btnReject}
          disabled={busy || !String(motivo).trim()}
          onClick={() => onReject(pid, motivo.trim())}
        >
          Rechazar
        </button>
      </div>
    </article>
  )
}
