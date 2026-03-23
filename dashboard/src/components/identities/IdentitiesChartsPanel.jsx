import { useMemo } from 'react'
import Card from '../ui/Card'
import RiskDistributionDots from '../charts/RiskDistributionDots'
import ThreatDistribution from '../charts/ThreatDistribution'
import ActivityHeatmap from '../charts/ActivityHeatmap'
import {
  threatDistributionForChart,
  activityHeatmapForChart,
} from '../../lib/chartMockHelpers'

/**
 * Panel F09 sobre la lista de identidades: dispersión, fuentes y heatmap con fallback mock.
 */
export default function IdentitiesChartsPanel({
  identities = [],
  events = [],
  onIdentityChartSelect,
  className = '',
}) {
  const threatData = useMemo(() => threatDistributionForChart(events), [events])
  const heatmapData = useMemo(() => activityHeatmapForChart(events), [events])
  const dotRows = useMemo(
    () =>
      identities.map((i) => ({
        ...i,
        score: Number(i.risk_score) || 0,
      })),
    [identities],
  )

  return (
    <div
      className={`grid grid-cols-1 gap-4 lg:grid-cols-3 ${className}`.trim()}
    >
      <Card className="flex min-h-0 flex-col p-4">
        <p className="mb-2 text-[11px] font-medium uppercase tracking-wider text-[var(--text-sec)]">
          Distribución de riesgo
        </p>
        <div className="min-h-[188px] flex-1">
          <RiskDistributionDots
            identities={dotRows}
            height={180}
            onIdentityClick={onIdentityChartSelect}
          />
        </div>
      </Card>
      <Card className="flex min-h-0 flex-col p-4">
        <p className="mb-2 text-[11px] font-medium uppercase tracking-wider text-[var(--text-sec)]">
          Por fuente
        </p>
        <ThreatDistribution data={threatData} />
      </Card>
      <Card className="flex min-h-0 flex-col overflow-x-auto p-4">
        <p className="mb-2 text-[11px] font-medium uppercase tracking-wider text-[var(--text-sec)]">
          Actividad (día × hora)
        </p>
        <ActivityHeatmap data={heatmapData} />
      </Card>
    </div>
  )
}
