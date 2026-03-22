import { useState } from 'react'
import styles from './ManualHypothesisModal.module.css'

const PLACEHOLDER =
  'Ej: Quiero investigar si hay dispositivos que se comunican con infraestructura de Tor o proxies anónimos...'

export function ManualHypothesisModal({ isOpen, onClose, onSubmit, busy }) {
  const [text, setText] = useState('')

  if (!isOpen) return null

  const handleSubmit = (e) => {
    e.preventDefault()
    const t = text.trim()
    if (t.length < 3 || busy) return
    onSubmit(t)
    setText('')
  }

  const handleClose = () => {
    if (!busy) {
      setText('')
      onClose()
    }
  }

  return (
    <div className={styles.backdrop} role="presentation" onClick={handleClose}>
      <div
        className={styles.modal}
        role="dialog"
        aria-modal="true"
        aria-labelledby="hunt-manual-title"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 id="hunt-manual-title" className={styles.title}>
          Nueva hipótesis manual
        </h2>
        <p className={styles.hint}>
          Describí en lenguaje natural qué querés investigar. El motor formaliza la hipótesis con IA; no hace falta
          escribir consultas técnicas.
        </p>
        <form onSubmit={handleSubmit}>
          <textarea
            className={styles.textarea}
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder={PLACEHOLDER}
            rows={6}
            maxLength={8000}
            disabled={busy}
            required
          />
          <div className={styles.actions}>
            <button type="button" className={styles.btnGhost} onClick={handleClose} disabled={busy}>
              Cancelar
            </button>
            <button type="submit" className={styles.btnPrimary} disabled={busy || text.trim().length < 3}>
              {busy ? 'Enviando…' : 'Formalizar hipótesis'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
