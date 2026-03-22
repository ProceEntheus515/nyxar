import styles from './LiveIndicator.module.css'

/**
 * Estado WebSocket + ritmo de eventos (F07).
 */
export default function LiveIndicator({ connected, eventsPerMin = 0, className = '' }) {
  const n = Math.max(0, Math.floor(Number(eventsPerMin) || 0))

  return (
    <div
      className={`${styles.wrap} ${className}`.trim()}
      role="status"
      aria-live="polite"
      aria-label={
        connected ? `Conectado, ${n} eventos por minuto` : 'Reconectando, sin conexión en vivo'
      }
    >
      <span
        className={`${styles.dot} ${connected ? `${styles.dotLive} animate-live` : styles.dotOff}`}
        aria-hidden
      />
      {connected ? (
        <span className={styles.rate}>
          {n} ev/min
        </span>
      ) : (
        <span className={styles.reconnect}>RECONECTANDO…</span>
      )}
    </div>
  )
}
