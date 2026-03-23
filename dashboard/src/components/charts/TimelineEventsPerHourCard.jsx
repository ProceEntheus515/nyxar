import { useMemo } from 'react'
import { eventsPerHourForChart } from '../../lib/chartMockHelpers'
import EventsPerHourBar from './EventsPerHourBar'

/**
 * Barras 24h: datos reales del buffer con fallback a MOCK_CHARTS si hay pocos eventos.
 */
export default function TimelineEventsPerHourCard({ events = [], className = '' }) {
  const data = useMemo(() => eventsPerHourForChart(events), [events])

  return (
    <div
      className={`rounded border border-[var(--base-border)] bg-[var(--base-surface)] p-3 ${className}`.trim()}
    >
      <p className="mb-2 text-[11px] font-medium uppercase tracking-wider text-[var(--text-sec)]">
        Eventos por hora
      </p>
      <EventsPerHourBar data={data} height={128} />
    </div>
  )
}
