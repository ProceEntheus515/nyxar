import React, { useState, useMemo, useCallback, useEffect } from 'react'
import { List, useListRef } from 'react-window'
import EventCard from '../components/data/EventCard'
import IncidentCard from '../components/data/IncidentCard'
import MetricCard from '../components/data/MetricCard'
import { useStore } from '../store'

function timelineRowHeight(index, { filteredEvents, alerts }) {
  const e = filteredEvents[index]
  if (!e) return 140
  const isIncident = alerts.some((al) => al.evento_original_id === e.id)
  return isIncident ? 252 : 138
}

function TimelineRow({
  index,
  style,
  ariaAttributes,
  filteredEvents,
  alerts,
  selectedEventId,
  onEventSelect,
}) {
  const e = filteredEvents[index]
  if (!e) return null

  const isIncident = alerts.some((al) => al.evento_original_id === e.id)
  const incidentData = alerts.find((al) => al.evento_original_id === e.id)
  const incidentMerged = isIncident
    ? {
        ...incidentData,
        interno: e.interno,
        timestamp: incidentData?.timestamp || e.timestamp,
      }
    : null

  const selected = selectedEventId != null && String(selectedEventId) === String(e.id)

  return (
    <div style={{ ...style, paddingBottom: '8px' }} {...ariaAttributes}>
      <div className="flex flex-col gap-2 h-full min-h-0">
        <EventCard
          event={e}
          selected={selected}
          onClick={() => onEventSelect?.(e)}
        />
        {isIncident && incidentMerged ? (
          <IncidentCard incident={incidentMerged} expandable={false} />
        ) : null}
      </div>
    </div>
  )
}

export default function Timeline() {
  const {
    events,
    alerts,
    timelineFocusEventId,
    setTimelineFocusEventId,
    detailPanel,
    openDetailPanel,
    closeDetailPanel,
  } = useStore()
  const [filterSource, setFilterSource] = useState('')
  const [isScrolled, setIsScrolled] = useState(false)
  const listRef = useListRef()

  const filteredEvents = useMemo(() => {
    let evts = events || []
    if (filterSource) {
      evts = evts.filter((e) => e.source?.toLowerCase().includes(filterSource))
    }
    return evts
  }, [events, filterSource])

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

  const linkedAlertsCount = useMemo(() => {
    const ids = new Set((filteredEvents || []).map((e) => e.id))
    return (alerts || []).filter((a) => ids.has(a.evento_original_id)).length
  }, [filteredEvents, alerts])

  const rowProps = useMemo(
    () => ({
      filteredEvents,
      alerts,
      selectedEventId,
      onEventSelect: handleEventSelect,
    }),
    [filteredEvents, alerts, selectedEventId, handleEventSelect],
  )

  useEffect(() => {
    if (!timelineFocusEventId || !filteredEvents.length) return
    const idx = filteredEvents.findIndex((ev) => ev.id === timelineFocusEventId)
    if (idx >= 0) {
      listRef.current?.scrollToRow({ index: idx, align: 'smart', behavior: 'smooth' })
    }
    setTimelineFocusEventId(null)
  }, [timelineFocusEventId, filteredEvents, setTimelineFocusEventId, listRef])

  const handleRowsRendered = useCallback((visible) => {
    setIsScrolled(visible.startIndex > 0)
  }, [])

  const scrollToTop = () => {
    listRef.current?.scrollToRow({ index: 0, behavior: 'instant' })
    setIsScrolled(false)
  }

  return (
    <div className="h-full flex flex-col relative w-full h-[calc(100vh-100px)]">
      <div className="mb-4 flex flex-shrink-0 flex-col gap-4">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <h2 className="text-xl font-semibold text-white">Live Event Timeline</h2>
          <select
            value={filterSource}
            onChange={(ev) => setFilterSource(ev.target.value)}
            className="bg-[var(--bg-card)] border border-[var(--border-default)] rounded p-2 text-sm text-white outline-none"
          >
            <option value="">Todas las Fuentes</option>
            <option value="dns">DNS</option>
            <option value="proxy">Proxy</option>
            <option value="firewall">Firewall</option>
            <option value="wazuh">Wazuh</option>
            <option value="misp">MISP</option>
          </select>
        </div>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          <MetricCard label="Eventos en vista" value={filteredEvents.length} />
          <MetricCard label="Buffer total" value={(events || []).length} />
          <MetricCard label="Alertas vinculadas" value={linkedAlertsCount} />
        </div>
      </div>

      {isScrolled && (
        <button
          type="button"
          onClick={scrollToTop}
          className="absolute top-16 left-1/2 -translate-x-1/2 z-10 bg-[var(--color-primary)] text-black px-4 py-1.5 rounded-full font-bold text-xs shadow-lg shadow-[var(--color-primary)]/20 animate-slide-in-right"
        >
          Volver arriba
        </button>
      )}

      <div className="flex-1 w-full relative">
        <List
          listRef={listRef}
          rowCount={filteredEvents.length}
          rowHeight={timelineRowHeight}
          rowComponent={TimelineRow}
          rowProps={rowProps}
          onRowsRendered={handleRowsRendered}
          style={{ height: 800, width: '100%' }}
        />
      </div>
    </div>
  )
}
