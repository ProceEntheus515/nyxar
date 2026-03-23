import CeoProgressBar from './CeoProgressBar'
import styles from './CeoViewHeader.module.css'

export default function CeoViewHeader({
  loading,
  progress,
  lastIso,
  lastRelativeLabel,
  onRefresh,
}) {
  return (
    <header className={styles.wrap}>
      <div className={styles.row}>
        <button
          type="button"
          className={styles.refresh}
          onClick={onRefresh}
          disabled={loading}
        >
          {loading ? 'Analizando…' : '⟳ Actualizar análisis'}
        </button>
        {lastIso ? (
          <p className={styles.meta}>
            Último análisis: <strong>{lastRelativeLabel}</strong>
          </p>
        ) : (
          <p className={styles.meta}>Aún no hay un análisis en esta sesión.</p>
        )}
      </div>
      {loading ? (
        <div className={styles.analyzing}>
          <span className={styles.analyzingLabel}>Progreso estimado</span>
          <CeoProgressBar value={progress} />
        </div>
      ) : null}
    </header>
  )
}
