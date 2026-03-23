import { useMemo, useId } from 'react'
import { AreaChart, Area, XAxis, YAxis } from 'recharts'
import { scoreToColor } from '../../lib/colors'
import { resolveToken } from './chartTokens'
import styles from './RiskSparkline.module.css'

/**
 * Evolución minimalista del risk score (F09). Sin tooltip.
 */
export default function RiskSparkline({
  data = [],
  width = 80,
  height = 32,
  className = '',
}) {
  const chartData = useMemo(
    () =>
      (Array.isArray(data) ? data : []).map((d, i) => ({
        i,
        score: Math.min(100, Math.max(0, Number(d.score) || 0)),
        timestamp: d.timestamp,
      })),
    [data],
  )

  const gid = useId().replace(/:/g, '')
  const lastScore = chartData[chartData.length - 1]?.score ?? 0
  const strokeVar = scoreToColor(lastScore).color
  const stroke = resolveToken(strokeVar) || strokeVar
  const chartW = Math.max(1, Math.round(Number(width) || 80))
  const chartH = Math.max(1, Math.round(Number(height) || 32))

  if (chartData.length === 0) {
    return (
      <div
        className={`${styles.empty} ${className}`.trim()}
        style={{ width, height }}
        aria-hidden
      />
    )
  }

  return (
    <div className={`${styles.wrap} ${className}`.trim()} style={{ width: chartW, height: chartH }}>
      <AreaChart
        width={chartW}
        height={chartH}
        data={chartData}
        margin={{ top: 4, right: 6, bottom: 4, left: 4 }}
      >
        <defs>
          <linearGradient id={`rsf-${gid}`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={stroke} stopOpacity={0.12} />
            <stop offset="100%" stopColor={stroke} stopOpacity={0.02} />
          </linearGradient>
        </defs>
        <XAxis dataKey="i" type="number" domain={['dataMin', 'dataMax']} hide />
        <YAxis domain={[0, 100]} hide />
        <Area
          type="monotone"
          dataKey="score"
          stroke={strokeVar}
          strokeWidth={1.5}
          fill={`url(#rsf-${gid})`}
          isAnimationActive={false}
          activeDot={false}
          dot={(dotProps) => {
            const { cx, cy, index, stroke } = dotProps
            if (index !== chartData.length - 1 || cx == null || cy == null) return null
            return <circle cx={cx} cy={cy} r={4} fill={stroke || strokeVar} stroke="none" />
          }}
        />
      </AreaChart>
    </div>
  )
}
