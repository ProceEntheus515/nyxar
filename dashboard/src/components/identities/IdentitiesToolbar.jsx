import { useMemo } from 'react'
import TimelineFilterDropdown, { TimelineFilterItem } from '../timeline/TimelineFilterDropdown'
import styles from './IdentitiesToolbar.module.css'

const SORT_OPTIONS = [
  { key: 'risk', dir: 'desc', label: 'Riesgo (mayor primero)' },
  { key: 'risk', dir: 'asc', label: 'Riesgo (menor primero)' },
  { key: 'name', dir: 'asc', label: 'Nombre A-Z' },
  { key: 'name', dir: 'desc', label: 'Nombre Z-A' },
  { key: 'area', dir: 'asc', label: 'Área A-Z' },
  { key: 'activity', dir: 'desc', label: 'Última actividad (reciente)' },
  { key: 'activity', dir: 'asc', label: 'Última actividad (antigua)' },
]

function sortLabel(sortColumn, sortDir) {
  const hit = SORT_OPTIONS.find((o) => o.key === sortColumn && o.dir === sortDir)
  return hit?.label || 'Ordenar'
}

function areasFromIdentities(list) {
  const set = new Set()
  for (const row of list || []) {
    const a = row?.area
    if (a && String(a).trim()) set.add(String(a).trim())
  }
  return [...set].sort((a, b) => a.localeCompare(b, 'es'))
}

/**
 * Búsqueda, filtros y orden para la vista Identidades (sin tabla HTML).
 */
export default function IdentitiesToolbar({
  search,
  onSearchChange,
  filterArea,
  onAreaChange,
  sortColumn,
  sortDir,
  onSortChange,
  soloActive,
  onSoloActiveChange,
  identityList,
}) {
  const areas = useMemo(() => areasFromIdentities(identityList), [identityList])
  const sortTrigger = `ORDENAR: ${sortLabel(sortColumn, sortDir).toUpperCase()}`

  return (
    <div className={styles.bar}>
      <label className={styles.searchWrap}>
        <span className="sr-only">Buscar identidad</span>
        <input
          type="search"
          className={styles.search}
          placeholder="Buscar identidad..."
          value={search}
          onChange={(ev) => onSearchChange(ev.target.value)}
          autoComplete="off"
        />
      </label>

      <TimelineFilterDropdown label={filterArea === '' ? 'ÁREA' : filterArea.toUpperCase()}>
        {(close) => (
          <>
            <TimelineFilterItem active={filterArea === ''} onPick={() => { onAreaChange(''); close(); }}>
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

      <TimelineFilterDropdown label={sortTrigger}>
        {(close) =>
          SORT_OPTIONS.map((opt) => (
            <TimelineFilterItem
              key={`${opt.key}-${opt.dir}`}
              active={sortColumn === opt.key && sortDir === opt.dir}
              onPick={() => {
                onSortChange(opt.key, opt.dir)
                close()
              }}
            >
              {opt.label}
            </TimelineFilterItem>
          ))
        }
      </TimelineFilterDropdown>

      <button
        type="button"
        className={`${styles.toggle} ${soloActive ? styles.toggleOn : ''}`.trim()}
        aria-pressed={soloActive}
        onClick={() => onSoloActiveChange(!soloActive)}
      >
        <span className={styles.toggleDot} aria-hidden>
          ◉
        </span>
        Solo activos
      </button>
    </div>
  )
}
