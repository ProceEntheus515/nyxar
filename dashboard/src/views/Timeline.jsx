import React, { useState, useMemo, useCallback, useEffect, useLayoutEffect, useRef } from 'react'
import { List, useListRef } from 'react-window'
import MetricCard from '../components/data/MetricCard'
import TimelineFilterBar from '../components/timeline/TimelineFilterBar'
import TimelineFeedRow from '../components/timeline/TimelineFeedRow'
import { normalizeSourceKey } from '../lib/colors'
import { useStore } from '../store'
import styles from './Timeline.module.css'

function startOfLocalDayMs(now = Date.now()) {
  const d = new Date(now)
  d.setHours(0, 0, 0, 0)
  return d.getTime()
}

function countEventsInRange(events, startMs, endMs) {
  let n = 0
  for (const e of events || []) {
    const t = new Date(e.timestamp).getTime()
    if (Number.isFinite(t) && t >= startMs && t < endMs) n += 1
  }
  return n
}

function countEventsSince(events, sinceMs) {
  let n = 0
  for (const e of events || []) {
    const t = new Date(e.timestamp).getTime()
    if (Number.isFinite(t) && t >= sinceMs) n += 1
  }
  return n
}

function honeypotsTodayCount(alerts, events) {
  const day = startOfLocalDayMs()
  let n = 0
  for (const a of alerts || []) {
    if (!String(a.tipo || '').toLowerCase().includes('honey')) continue
    const t = new Date(a.timestamp).getTime()
    if (Number.isFinite(t) && t >= day) n += 1
  }
  for (const e of events || []) {
    if (!String(e.source || '').toLowerCase().includes('honey')) continue
    const t = new Date(e.timestamp).getTime()
    if (Number.isFinite(t) && t >= day) n += 1
  }
  return n
}

export default function Timeline() {
  const {
    events,
    alerts,
    incidents,
    stats,
    timelineFocusEventId,
    setTimelineFocusEventId,
    detailPanel,
    openDetailPanel,
    closeDetailPanel,
  } = useStore()

  const [filterSource, setFilterSource] = useState('')
  const [filterMinRisk, setFilterMinRisk] = useState(0)
  const [filterArea, setFilterArea] = useState('')
  const [soloAlertas, setSoloAlertas] = useState(false)
  const [feedDensity, setFeedDensity] = useState('compact')
  const [pendingNew, setPendingNew] = useState(0)

  const listRef = useListRef()
  const feedWrapRef = useRef(null)
  const [listHeight, setListHeight] = useState(480)
  const wasAtTopRef = useRef(true)
  const anchorHeadIdRef = useRef(null)

  const rowPx = feedDensity === 'compact' ? 76 : 120
  const compactFeed = feedDensity === 'compact'

  const alertEventIds = useMemo(
    () => new Set((alerts || []).map((a) => a.evento_original_id).filter(Boolean)),
    [alerts],
  )

  const filteredEvents = useMemo(() => {
    let evts = events || []
    if (filterSource) {
      evts = evts.filter((e) => normalizeSourceKey(e.source) === filterSource)
    }
    if (filterMinRisk > 0) {
      evts = evts.filter((e) => Number(e.enrichment?.risk_score || 0) >= filterMinRisk)
    }
    if (filterArea) {
      evts = evts.filter((e) => (e.interno?.area || '') === filterArea)
    }
    if (soloAlertas) {
      evts = evts.filter((e) => alertEventIds.has(e.id))
    }
    return evts
  }, [events, filterSource, filterMinRisk, filterArea, soloAlertas, alertEventIds])

  const filterFingerprint = `${filterSource}|${filterMinRisk}|${filterArea}|${soloAlertas}`

  const selectedEventId =
    detailPanel.isOpen && detailPanel.type === 'event' ? detailPanel.id : null

  const handleEventSelect = useCallback(
    (ev) => {
      if (!ev?.id) return
      const same =
        detailPanel.isOpen &&
        detailPanel.type === 'event' &&
        String(detailPanel.id) === String(ev.id)
      if (same) closeDetailPanel()
      else openDetailPanel('event', ev.id)
    },
    [detailPanel, openDetailPanel, closeDetailPanel],
  )

  const rowProps = useMemo(
    () => ({
      filteredEvents,
      selectedEventId,
      onEventSelect: handleEventSelect,
      compactFeed,
    }),
    [filteredEvents, selectedEventId, handleEventSelect, compactFeed],
  )

  const now = Date.now()
  const todayStart = startOfLocalDayMs(now)
  const yesterdayStart = todayStart - 86400000
  const eventsToday = countEventsInRange(events, todayStart, now + 1)
  const eventsYesterday = countEventsInRange(events, yesterdayStart, todayStart)
  const deltaDay = eventsToday - eventsYesterday

  const oneMinAgo = now - 60000
  const eventsPerMin = countEventsSince(events, oneMinAgo)

  const openIncidents = (incidents || []).filter(
    (i) => String(i.estado || '').toLowerCase() === 'abierto',
  ).length
  const openAlertsCount = Number.isFinite(Number(stats?.alertas_abiertas))
    ? Number(stats.alertas_abiertas)
    : openIncidents + (alerts || []).length

  const honeypotsToday = honeypotsTodayCount(alerts, events)

  useLayoutEffect(() => {
    const el = feedWrapRef.current
    if (!el || typeof ResizeObserver === 'undefined') return
    const ro = new ResizeObserver(() => {
      const h = el.clientHeight
      setListHeight(Math.max(200, Math.floor(h)))
    })
    ro.observe(el)
    setListHeight(Math.max(200, Math.floor(el.clientHeight)))
    return () => ro.disconnect()
  }, [])

  useEffect(() => {
    if (!timelineFocusEventId || !filteredEvents.length) return
    const idx = filteredEvents.findIndex((ev) => ev.id === timelineFocusEventId)
    if (idx >= 0) {
      listRef.current?.scrollToRow({ index: idx, align: 'smart', behavior: 'smooth' })
    }
    setTimelineFocusEventId(null)
  }, [timelineFocusEventId, filteredEvents, setTimelineFocusEventId, listRef])

  const onRowsRendered = useCallback(
    ({ startIndex }) => {
      if (startIndex === 0) {
        wasAtTopRef.current = true
        anchorHeadIdRef.current = null
        setPendingNew(0)
        return
      }
      if (wasAtTopRef.current && startIndex > 0) {
        anchorHeadIdRef.current = events[0]?.id ?? null
        wasAtTopRef.current = false
      }
    },
    [events],
  )

  useEffect(() => {
    const head = events[0]?.id
    if (head == null || anchorHeadIdRef.current == null) return
    if (head === anchorHeadIdRef.current) return
    const idx = events.findIndex((e) => e.id === anchorHeadIdRef.current)
    const n = idx === -1 ? Math.min(500, events.length) : idx
    setPendingNew(n)
  }, [events])

  const scrollToTopSmooth = useCallback(() => {
    listRef.current?.scrollToRow({ index: 0, align: 'start', behavior: 'smooth' })
    anchorHeadIdRef.current = null
    setPendingNew(0)
    wasAtTopRef.current = true
  }, [listRef])

  return (
    <div className={styles.page}>
      <div className={styles.headerBlock}>
        <div className={styles.titleRow}>
          <h2 className={styles.title}>Live Event Timeline</h2>
          <div className={styles.densityToggle} role="group" aria-label="Densidad del feed">
            <button
              type="button"
              className={`${styles.densityBtn} ${feedDensity === 'compact' ? styles.densityBtnActive : ''}`.trim()}
              onClick={() => setFeedDensity('compact')}
            >
              Compacto
            </button>
            <button
              type="button"
              className={`${styles.densityBtn} ${feedDensity === 'expanded' ? styles.densityBtnActive : ''}`.trim()}
              onClick={() => setFeedDensity('expanded')}
            >
              Expandido
            </button>
          </div>
        </div>

        <div className={styles.metrics}>
          <MetricCard
            label="Eventos hoy"
            value={eventsToday}
            delta={deltaDay}
            trend
          />
          <MetricCard label="Eventos/min ahora" value={eventsPerMin} />
          <MetricCard
            label="Alertas abiertas"
            value={openAlertsCount}
            className={openAlertsCount > 0 ? styles.metricAlertsOpen : ''}
          />
          <MetricCard
            label="Honeypots activados hoy"
            value={honeypotsToday}
            className={honeypotsToday > 0 ? styles.metricHoneypotHot : ''}
          />
        </div>

        <TimelineFilterBar
          events={events}
          filterSource={filterSource}
          onSourceChange={setFilterSource}
          filterMinRisk={filterMinRisk}
          onMinRiskChange={setFilterMinRisk}
          filterArea={filterArea}
          onAreaChange={setFilterArea}
          soloAlertas={soloAlertas}
          onSoloAlertasChange={setSoloAlertas}
        />
      </div>

      <div className={styles.feedWrap} ref={feedWrapRef}>
        {pendingNew > 0 ? (
          <button type="button" className={styles.badgeNew} onClick={scrollToTopSmooth}>
            ▲ {pendingNew} nuevo{pendingNew === 1 ? '' : 's'}
          </button>
        ) : null}

        <div
          key={`${filterFingerprint}-${rowPx}`}
          className={`${styles.listAnim} animate-fadeIn`.trim()}
        >
          <List
            listRef={listRef}
            rowCount={filteredEvents.length}
            rowHeight={rowPx}
            rowComponent={TimelineFeedRow}
            rowProps={rowProps}
            onRowsRendered={onRowsRendered}
            style={{ height: listHeight, width: '100%' }}
          />
        </div>
      </div>
    </div>
  )
}
