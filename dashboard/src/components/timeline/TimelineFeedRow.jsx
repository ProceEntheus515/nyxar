import {
  TargetListRow,
  eventToTimelineTargetItem,
  TIMELINE_TARGET_COLUMNS,
} from '../data/TargetList'
import styles from './TimelineFeedRow.module.css'

const THIRTY_MIN_MS = 30 * 60 * 1000

function formatRelativeGap(ms) {
  const m = Math.floor(ms / 60000)
  if (m < 1) return 'hace instantes'
  if (m < 60) return `hace ${m} min`
  const h = Math.floor(m / 60)
  if (h < 24) return `hace ${h} h`
  const d = Math.floor(h / 24)
  return `hace ${d} d`
}

function parseTs(iso) {
  const t = new Date(iso).getTime()
  return Number.isFinite(t) ? t : 0
}

/**
 * Fila virtualizada del Timeline: TargetList (F08) + separador temporal en overlay.
 * react-window v2 hace spread de rowProps en la raíz del row.
 */
export default function TimelineFeedRow({
  index,
  style,
  ariaAttributes,
  filteredEvents,
  selectedEventId,
  onEventSelect,
  compactFeed,
  targetColumns = TIMELINE_TARGET_COLUMNS,
}) {
  if (!filteredEvents) return null
  const e = filteredEvents[index]
  if (!e) return null

  const prev = index > 0 ? filteredEvents[index - 1] : null
  let showSep = false
  let sepText = ''
  if (prev && e.timestamp && prev.timestamp) {
    const gap = parseTs(prev.timestamp) - parseTs(e.timestamp)
    if (gap > THIRTY_MIN_MS) {
      showSep = true
      sepText = formatRelativeGap(gap)
    }
  }

  const selected = selectedEventId != null && String(selectedEventId) === String(e.id)
  const item = eventToTimelineTargetItem(e)

  return (
    <div style={style} {...ariaAttributes} className={styles.cell}>
      {showSep ? (
        <div className={styles.sepOverlay} aria-hidden>
          <span className={styles.sepLine} />
          <span className={styles.sepLabel}>{sepText}</span>
          <span className={styles.sepLine} />
        </div>
      ) : null}
      <div className={`${styles.body} ${showSep ? styles.bodyWithSep : ''}`.trim()}>
        {item ? (
          <TargetListRow
            item={item}
            columns={targetColumns}
            isSelected={selected}
            onSelect={() => onEventSelect?.(e)}
            enableChildren={false}
            showSubtitle={!compactFeed}
          />
        ) : null}
      </div>
    </div>
  )
}
