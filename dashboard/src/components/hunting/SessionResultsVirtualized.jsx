import { List, useListRef } from 'react-window'
import { summarizeHuntDoc, pickEventId } from '../../lib/huntingUtils'
import styles from './SessionResultsVirtualized.module.css'

const ROW_H = 76

export function HuntResultCard({ row, onOpenTimeline }) {
  if (!row) return null
  const s = summarizeHuntDoc(row.doc)
  const evtId = pickEventId(row.doc)

  return (
    <div className={styles.row}>
      <div className={styles.rowTop}>
        <span className={styles.mono}>{s.timestamp || '—'}</span>
        {evtId && (
          <button type="button" className={styles.linkBtn} onClick={() => onOpenTimeline(evtId)}>
            Ver en Timeline
          </button>
        )}
      </div>
      <div className={styles.rowGrid}>
        <div>
          <span className={styles.lbl}>Identidad</span>
          <span className={styles.val}>{s.identidad}</span>
        </div>
        <div>
          <span className={styles.lbl}>Valor</span>
          <span className={styles.val}>{s.valor}</span>
        </div>
        <div className={styles.span2}>
          <span className={styles.lbl}>Contexto</span>
          <span className={styles.val}>{s.contexto}</span>
        </div>
      </div>
      <p className={styles.qref}>{row.queryLabel}</p>
    </div>
  )
}

function HuntResultRow({ index, style, ariaAttributes, rowProps }) {
  const { rows, onOpenTimeline } = rowProps
  const row = rows[index]
  if (!row) return null
  return (
    <div style={{ ...style, paddingBottom: 6 }} {...ariaAttributes}>
      <HuntResultCard row={row} onOpenTimeline={onOpenTimeline} />
    </div>
  )
}

export function SessionResultsVirtualized({ rows, onOpenTimeline, listHeight }) {
  const listRef = useListRef()
  const h = Math.min(Math.max(listHeight || 420, 200), 560)
  const rowProps = { rows: rows || [], onOpenTimeline }

  if (!rows || rows.length === 0) {
    return <p className={styles.empty}>No hay documentos en la muestra de resultados.</p>
  }

  if (rows.length <= 50) {
    return (
      <div className={styles.simpleList}>
        {rows.map((row) => (
          <div key={row.rowKey} className={styles.simpleItem}>
            <HuntResultCard row={row} onOpenTimeline={onOpenTimeline} />
          </div>
        ))}
      </div>
    )
  }

  return (
    <div className={styles.virtualWrap}>
      <p className={styles.virtualNote}>
        Mostrando {rows.length} filas virtualizadas (solo se renderizan las visibles).
      </p>
      <List
        listRef={listRef}
        rowCount={rows.length}
        rowHeight={ROW_H}
        rowComponent={HuntResultRow}
        rowProps={rowProps}
        style={{ height: h, width: '100%' }}
      />
    </div>
  )
}
