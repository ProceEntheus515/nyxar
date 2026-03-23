import { useMemo } from 'react'
import { SOURCE_COLORS, normalizeSourceKey } from '../../lib/colors'
import TimelineFilterDropdown, { TimelineFilterItem } from './TimelineFilterDropdown'
import styles from './TimelineFilterBar.module.css'

const SEVERITY_OPTIONS = [
  { value: 0, label: 'Cualquiera' },
  { value: 40, label: 'Medio o más' },
  { value: 60, label: 'Alto o más' },
  { value: 80, label: 'Crítico' },
]

function sourceKeysFromEvents(events) {
  const set = new Set(Object.keys(SOURCE_COLORS))
  for (const ev of events || []) {
    const k = normalizeSourceKey(ev?.source)
    if (k) set.add(k)
  }
  return [...set].sort()
}

function areasFromEvents(events) {
  const set = new Set()
  for (const ev of events || []) {
    const a = ev?.interno?.area
    if (a && String(a).trim()) set.add(String(a).trim())
  }
  return [...set].sort((a, b) => a.localeCompare(b, 'es'))
}

/**
 * Una línea de filtros AND para el Timeline (F08).
 */
export default function TimelineFilterBar({
  events,
  filterSource,
  onSourceChange,
  filterMinRisk,
  onMinRiskChange,
  filterArea,
  onAreaChange,
  soloAlertas,
  onSoloAlertasChange,
}) {
  const sourceKeys = useMemo(() => sourceKeysFromEvents(events), [events])
  const areas = useMemo(() => areasFromEvents(events), [events])

  const sourceLabel =
    filterSource === ''
      ? 'TODAS LAS FUENTES'
      : SOURCE_COLORS[filterSource]?.label || filterSource.toUpperCase()

  const sevLabel =
    SEVERITY_OPTIONS.find((o) => o.value === filterMinRisk)?.label || 'SEVERIDAD MÍNIMA'

  const areaLabel = filterArea === '' ? 'ÁREA' : filterArea

  return (
    <div className={styles.bar}>
      <TimelineFilterDropdown label={sourceLabel}>
        {(close) => (
          <>
            <TimelineFilterItem
              active={filterSource === ''}
              onPick={() => {
                onSourceChange('')
                close()
              }}
            >
              Todas las fuentes
            </TimelineFilterItem>
            {sourceKeys.map((key) => {
              const meta = SOURCE_COLORS[key] || { icon: '·', label: key, color: 'var(--base-muted)' }
              return (
                <TimelineFilterItem
                  key={key}
                  active={filterSource === key}
                  onPick={() => {
                    onSourceChange(key)
                    close()
                  }}
                >
                  <span className={styles.sourceIcon} style={{ color: meta.color }} aria-hidden>
                    {meta.icon}
                  </span>
                  {meta.label}
                </TimelineFilterItem>
              )
            })}
          </>
        )}
      </TimelineFilterDropdown>

      <TimelineFilterDropdown label={sevLabel}>
        {(close) =>
          SEVERITY_OPTIONS.map((opt) => (
            <TimelineFilterItem
              key={opt.value}
              active={filterMinRisk === opt.value}
              onPick={() => {
                onMinRiskChange(opt.value)
                close()
              }}
            >
              {opt.label}
            </TimelineFilterItem>
          ))
        }
      </TimelineFilterDropdown>

      <TimelineFilterDropdown label={areaLabel}>
        {(close) => (
          <>
            <TimelineFilterItem
              active={filterArea === ''}
              onPick={() => {
                onAreaChange('')
                close()
              }}
            >
              Todas las áreas
            </TimelineFilterItem>
            {areas.map((a) => (
              <TimelineFilterItem
                key={a}
                active={filterArea === a}
                onPick={() => {
                  onAreaChange(a)
                  close()
                }}
              >
                {a}
              </TimelineFilterItem>
            ))}
          </>
        )}
      </TimelineFilterDropdown>

      <button
        type="button"
        className={`${styles.toggle} ${soloAlertas ? styles.toggleOn : ''}`.trim()}
        aria-pressed={soloAlertas}
        onClick={() => onSoloAlertasChange(!soloAlertas)}
      >
        <span className={styles.toggleIcon} aria-hidden>
          ≡
        </span>
        Solo alertas
      </button>
    </div>
  )
}
