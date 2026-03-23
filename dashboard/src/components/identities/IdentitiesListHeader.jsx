import styles from './IdentitiesListHeader.module.css'

/**
 * Cabecera de columnas (CSS Grid, no tabla HTML). Clicks alternan orden.
 */
export default function IdentitiesListHeader({ sortColumn, sortDir, onColumnSort }) {
  const riskIndicator = sortColumn === 'risk' ? (sortDir === 'desc' ? '↓' : '↑') : ''
  const nameIndicator = sortColumn === 'name' ? (sortDir === 'desc' ? '↓' : '↑') : ''
  const areaIndicator = sortColumn === 'area' ? (sortDir === 'desc' ? '↓' : '↑') : ''
  const actIndicator = sortColumn === 'activity' ? (sortDir === 'desc' ? '↓' : '↑') : ''

  return (
    <div className={styles.header} role="row">
      <span className={styles.ph} aria-hidden />
      <button type="button" className={styles.headBtn} onClick={() => onColumnSort('name')}>
        Identidad {nameIndicator}
      </button>
      <span className={styles.phDot} aria-hidden />
      <button type="button" className={styles.headBtn} onClick={() => onColumnSort('area')}>
        Área {areaIndicator}
      </button>
      <button type="button" className={styles.headBtnSmall} onClick={() => onColumnSort('activity')}>
        24H {actIndicator}
      </button>
      <button type="button" className={styles.headBtnEnd} onClick={() => onColumnSort('risk')}>
        Riesgo {riskIndicator}
      </button>
    </div>
  )
}
