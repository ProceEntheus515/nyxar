import { useMemo, useCallback } from 'react'
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
} from 'recharts'
import { readCssVar } from '../../styles/cssVar'
import { resolveToken } from './chartTokens'
import tt from './ChartTooltip.module.css'
import styles from './EventsPerHourBar.module.css'

function buildHours(data) {
  const byH = new Map()
  ;(Array.isArray(data) ? data : []).forEach((d) => {
    const h = Number(d.hour)
    if (h >= 0 && h <= 23) byH.set(h, Math.max(0, Number(d.count) || 0))
  })
  return Array.from({ length: 24 }, (_, hour) => ({
    hour,
    count: byH.get(hour) ?? 0,
  }))
}

function EventsTooltip({ active, payload }) {
  if (!active || !payload?.length) return null
  const row = payload[0].payload
  return (
    <div className={tt.wrap}>
      <p className={tt.label}>Eventos</p>
      <p className={tt.value}>
        {row.count} eventos a las {row.hour}:00
      </p>
    </div>
  )
}

/**
 * 24 barras por hora; opacidad según volumen; hora actual resaltada (F09).
 */
export default function EventsPerHourBar({ data = [], height = 120, className = '' }) {
  const chartData = useMemo(() => buildHours(data), [data])
  const max = useMemo(() => Math.max(1, ...chartData.map((d) => d.count)), [chartData])
  const currentHour = new Date().getHours()
  const cyanBase = readCssVar('--cyan-base') || '#38b2cc'
  const subtle = resolveToken('var(--base-subtle)') || '#6b7fa0'
  const border = readCssVar('--base-border') || '#1f2b40'

  const barShape = useCallback(
    (props) => {
      const { x, y, width, height, payload, index } = props
      if (width == null || height == null) return null
      const opacity = 0.12 + (payload.count / max) * 0.75
      const isNow = payload.hour === currentHour
      const strokeC = isNow ? resolveToken('var(--cyan-bright)') || cyanBase : 'transparent'
      return (
        <rect
          x={x}
          y={y}
          width={width}
          height={height}
          rx={1}
          ry={1}
          fill={cyanBase}
          fillOpacity={opacity}
          stroke={strokeC}
          strokeWidth={isNow ? 2 : 0}
          className={styles.barEnter}
          style={{ animationDelay: `${(index ?? 0) * 40}ms` }}
        />
      )
    },
    [max, currentHour, cyanBase],
  )

  const cursorFill = useMemo(() => {
    const s = readCssVar('--base-surface')
    if (!s) return 'rgba(17,22,32,0.25)'
    return s.startsWith('#') && s.length === 7 ? `${s}40` : 'rgba(17,22,32,0.2)'
  }, [])

  const barH = Math.max(1, Math.round(Number(height) || 120))

  return (
    <div className={`${styles.wrap} ${className}`.trim()} style={{ width: '100%', height: barH }}>
      <ResponsiveContainer
        width="100%"
        height="100%"
        minWidth={0}
        minHeight={barH}
        initialDimension={{ width: 480, height: barH }}
      >
        <BarChart
          data={chartData}
          margin={{ top: 8, right: 8, left: 4, bottom: 28 }}
          barCategoryGap={4}
          maxBarSize={6}
        >
          <XAxis
            dataKey="hour"
            type="category"
            tick={{ fill: subtle, fontSize: 11, fontFamily: 'var(--font-data)' }}
            tickLine={false}
            axisLine={{ stroke: border }}
            ticks={[0, 6, 12, 18, 23]}
            tickFormatter={(h) => (h === 23 ? '24' : String(h))}
            interval={0}
          />
          <YAxis hide domain={[0, max]} />
          <Tooltip
            cursor={{ fill: cursorFill }}
            content={<EventsTooltip />}
            wrapperStyle={{ outline: 'none' }}
          />
          <Bar dataKey="count" shape={barShape} isAnimationActive={false} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
