import { useSyncExternalStore } from 'react'
import {
  subscribeToasts,
  getToastSnapshot,
  dismissToast,
} from '../../lib/toastBus'
import styles from './ToastHost.module.css'

function toastKindClass(type) {
  if (type === 'warning') return styles.kindWarning
  if (type === 'error') return styles.kindError
  return styles.kindInfo
}

export default function ToastHost() {
  const list = useSyncExternalStore(subscribeToasts, getToastSnapshot, getToastSnapshot)

  if (!list.length) return null

  return (
    <div className={styles.region} role="region" aria-label="Notificaciones">
      {list.map((t) => (
        <div
          key={t.id}
          className={`${styles.toast} ${toastKindClass(t.type)}`.trim()}
          role="status"
        >
          <div className={styles.head}>
            <span className={styles.title}>{t.title}</span>
            <button
              type="button"
              className={styles.close}
              onClick={() => dismissToast(t.id)}
              aria-label="Cerrar notificación"
            >
              ×
            </button>
          </div>
          {t.message ? <p className={styles.msg}>{t.message}</p> : null}
        </div>
      ))}
    </div>
  )
}
