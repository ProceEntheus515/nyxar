import { useStore } from '../../store'
import EventDetailContent from '../timeline/EventDetailContent'
import IdentityDetailContent from '../identities/IdentityDetailContent'
import styles from './DetailPanel.module.css'

const TYPE_LABEL = {
  identity: 'Identidad',
  event: 'Evento',
  incident: 'Incidente',
  honeypot: 'Honeypot',
}

function panelTitle(type) {
  return TYPE_LABEL[type] || 'Detalle'
}

export default function DetailPanel({ wideLayout }) {
  const { detailPanel, closeDetailPanel } = useStore()
  const { type, id, isOpen } = detailPanel

  if (!isOpen) return null

  return (
    <>
      {!wideLayout ? (
        <button type="button" className={styles.backdrop} onClick={closeDetailPanel} aria-label="Cerrar panel" />
      ) : null}
      <aside className={styles.column} aria-label="Panel de detalle">
        <div className={styles.header}>
          <h2 className={styles.title}>{panelTitle(type)}</h2>
          <button type="button" className={styles.close} onClick={closeDetailPanel}>
            Cerrar
          </button>
        </div>
        <div className={styles.body}>
          {type === 'event' && id != null ? (
            <EventDetailContent eventId={id} />
          ) : type === 'identity' && id != null ? (
            <IdentityDetailContent identityId={id} />
          ) : (
            <>
              <p className={styles.placeholder}>
                Tipo: {type || '—'}
                <br />
                ID: {id != null ? String(id) : '—'}
              </p>
              <p className={styles.placeholder}>
                El contenido contextual (mapa, timeline, incidentes) se enlaza aquí vía openDetailPanel(type, id).
              </p>
            </>
          )}
        </div>
      </aside>
    </>
  )
}
