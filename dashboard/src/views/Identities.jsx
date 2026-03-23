import React, { useCallback, useLayoutEffect, useMemo, useRef, useState } from 'react'
import { List, useListRef } from 'react-window'
import { useStore } from '../store'
import MetricCard from '../components/data/MetricCard'
import IdentitiesToolbar from '../components/identities/IdentitiesToolbar'
import IdentitiesListHeader from '../components/identities/IdentitiesListHeader'
import IdentityVirtualRow from '../components/identities/IdentityVirtualRow'
import { isIdentityActiveLast30m } from '../lib/identityBehavior'
import styles from './Identities.module.css'

const ROW_HEIGHT = 58

function compareIdentities(a, b, col, dir) {
  const m = dir === 'asc' ? 1 : -1
  if (col === 'risk') {
    return m * ((Number(a.risk_score) || 0) - (Number(b.risk_score) || 0))
  }
  if (col === 'name') {
    return m * String(a.nombre_completo || '').localeCompare(String(b.nombre_completo || ''), 'es')
  }
  if (col === 'area') {
    return m * String(a.area || '').localeCompare(String(b.area || ''), 'es')
  }
  if (col === 'activity') {
    const ta = new Date(a.last_seen_ts || 0).getTime()
    const tb = new Date(b.last_seen_ts || 0).getTime()
    return m * (ta - tb)
  }
  return 0
}

function matchesSearch(row, q) {
  if (!q) return true
  const s = q.toLowerCase()
  const parts = [
    row.nombre_completo,
    row.dispositivo,
    row.hostname,
    row.area,
    row.id,
    row.ip_asociada,
  ]
    .filter(Boolean)
    .map((x) => String(x).toLowerCase())
  return parts.some((p) => p.includes(s))
}

export default function Identities() {
  const identities = useStore((s) => s.identities)
  const openDetailPanel = useStore((s) => s.openDetailPanel)
  const closeDetailPanel = useStore((s) => s.closeDetailPanel)
  const detailPanel = useStore((s) => s.detailPanel)
  const huntingIdentityIds = useStore((s) => s.huntingIdentityIds)
  const huntingSessionIdentityIds = useStore((s) => s.huntingSessionIdentityIds)

  const [search, setSearch] = useState('')
  const [filterArea, setFilterArea] = useState('')
  const [sortColumn, setSortColumn] = useState('risk')
  const [sortDir, setSortDir] = useState('desc')
  const [soloActive, setSoloActive] = useState(false)

  const listRef = useListRef()
  const listWrapRef = useRef(null)
  const [listHeight, setListHeight] = useState(420)

  const allRows = useMemo(() => Object.values(identities || {}), [identities])

  const huntingSet = useMemo(() => {
    const a = (huntingIdentityIds || []).map(String)
    const b = (huntingSessionIdentityIds || []).map(String)
    return new Set([...a, ...b])
  }, [huntingIdentityIds, huntingSessionIdentityIds])

  const filtered = useMemo(() => {
    let rows = allRows
    if (search.trim()) {
      const q = search.trim()
      rows = rows.filter((r) => matchesSearch(r, q))
    }
    if (filterArea) {
      rows = rows.filter((r) => String(r.area || '') === filterArea)
    }
    if (soloActive) {
      rows = rows.filter((r) => isIdentityActiveLast30m(r.last_seen_ts))
    }
    return rows
  }, [allRows, search, filterArea, soloActive])

  const sortedRows = useMemo(() => {
    const copy = [...filtered]
    copy.sort((a, b) => compareIdentities(a, b, sortColumn, sortDir))
    return copy
  }, [filtered, sortColumn, sortDir])

  const metrics = useMemo(() => {
    const total = allRows.length
    let active = 0
    let highRisk = 0
    let priv = 0
    for (const r of allRows) {
      if (isIdentityActiveLast30m(r.last_seen_ts)) active += 1
      if (Number(r.risk_score) > 60) highRisk += 1
      if (r.es_privilegiado) priv += 1
    }
    return { total, active, highRisk, priv }
  }, [allRows])

  const selectedId =
    detailPanel.isOpen && detailPanel.type === 'identity' ? detailPanel.id : null

  const handleSelect = useCallback(
    (id) => {
      if (id == null) return
      const same =
        detailPanel.isOpen && detailPanel.type === 'identity' && String(detailPanel.id) === String(id)
      if (same) closeDetailPanel()
      else openDetailPanel('identity', id)
    },
    [detailPanel, openDetailPanel, closeDetailPanel],
  )

  const handleColumnSort = useCallback(
    (col) => {
      if (sortColumn === col) {
        setSortDir((d) => (d === 'desc' ? 'asc' : 'desc'))
      } else {
        setSortColumn(col)
        setSortDir(col === 'risk' || col === 'activity' ? 'desc' : 'asc')
      }
    },
    [sortColumn],
  )

  const handleSortFromToolbar = useCallback((col, dir) => {
    setSortColumn(col)
    setSortDir(dir)
  }, [])

  useLayoutEffect(() => {
    const el = listWrapRef.current
    if (!el || typeof ResizeObserver === 'undefined') return
    const ro = new ResizeObserver(() => {
      setListHeight(Math.max(200, Math.floor(el.clientHeight)))
    })
    ro.observe(el)
    setListHeight(Math.max(200, Math.floor(el.clientHeight)))
    return () => ro.disconnect()
  }, [])

  const rowProps = useMemo(
    () => ({
      rows: sortedRows,
      selectedId,
      onSelect: handleSelect,
      huntingSet,
    }),
    [sortedRows, selectedId, handleSelect, huntingSet],
  )

  return (
    <div className={styles.page}>
      <h2 className={styles.title}>Identidades en riesgo</h2>

      <div className={styles.metrics}>
        <MetricCard label="Total monitoreadas" value={metrics.total} />
        <MetricCard label="Activas ahora (30 min)" value={metrics.active} />
        <MetricCard label="En riesgo alto (>60)" value={metrics.highRisk} />
        <MetricCard label="Administradores privilegiados" value={metrics.priv} />
      </div>

      <div className={styles.toolbarWrap}>
        <IdentitiesToolbar
          search={search}
          onSearchChange={setSearch}
          filterArea={filterArea}
          onAreaChange={setFilterArea}
          sortColumn={sortColumn}
          sortDir={sortDir}
          onSortChange={handleSortFromToolbar}
          soloActive={soloActive}
          onSoloActiveChange={setSoloActive}
          identityList={allRows}
        />
      </div>

      <div className={styles.listRegion} ref={listWrapRef}>
        <IdentitiesListHeader
          sortColumn={sortColumn}
          sortDir={sortDir}
          onColumnSort={handleColumnSort}
        />
        {sortedRows.length === 0 ? (
          <p className={styles.empty}>No hay identidades que coincidan con los filtros.</p>
        ) : (
          <List
            listRef={listRef}
            rowCount={sortedRows.length}
            rowHeight={ROW_HEIGHT}
            rowComponent={IdentityVirtualRow}
            rowProps={rowProps}
            style={{ height: listHeight, width: '100%' }}
          />
        )}
      </div>
    </div>
  )
}
