import styles from './NetworkMapToolbar.module.css'

/**
 * Controles del mapa de red (spec PROMPTS_V3 F09).
 * `bar`: fila compacta fuera del canvas; `stacked`: columna (legacy).
 */
export default function NetworkMapToolbar({
  showConnections,
  onToggleConnections,
  minSeverity,
  onMinSeverityChange,
  activeOnly,
  onToggleActiveOnly,
  onCenterView,
  variant = 'bar',
}) {
  const root = variant === 'bar' ? styles.wrapBar : styles.wrap
  const btnClass = variant === 'bar' ? styles.btnInline : styles.btn

  return (
    <div className={root}>
      <label className={styles.row}>
        <input
          type="checkbox"
          checked={showConnections}
          onChange={(e) => onToggleConnections(e.target.checked)}
        />
        <span>Conexiones</span>
      </label>

      <label
        className={`${styles.row} ${variant === 'bar' ? styles.scoreBlock : ''}`}
        title="Solo nodos con riesgo mayor o igual a este valor. El tope es 99."
      >
        <span className={styles.labelNarrow}>Score mín.</span>
        <input
          type="range"
          min={0}
          max={99}
          value={Math.min(99, minSeverity)}
          onChange={(e) => onMinSeverityChange(Number(e.target.value))}
          className={styles.range}
        />
        <span className={styles.badge}>{Math.min(99, minSeverity)}</span>
      </label>

      <label className={styles.row}>
        <input
          type="checkbox"
          checked={activeOnly}
          onChange={(e) => onToggleActiveOnly(e.target.checked)}
        />
        <span>Solo activos (5 min)</span>
      </label>

      <button type="button" className={btnClass} onClick={onCenterView}>
        Centrar vista
      </button>
    </div>
  )
}
