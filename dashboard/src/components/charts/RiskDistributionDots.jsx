import { useMemo, useCallback } from 'react'
import {
  ResponsiveContainer,
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  Tooltip,
} from 'recharts'
import { scoreToColor } from '../../lib/colors'
import { useStore } from '../../store'
import { readCssVar } from '../../styles/cssVar'
import { resolveToken } from './chartTokens'
import tt from './ChartTooltip.module.css'
import styles from './RiskDistributionDots.module.css'

function layoutPoints(identities) {
  const list = Array.isArray(identities) ? identities : []
  const buckets = new Map()
  for (const row of list) {
    const s = Math.round(Math.min(100, Math.max(0, Number(row.score) || 0)))
    if (!buckets.has(s)) buckets.set(s, [])
    buckets.get(s).push(row)
  }
  const out = []
  const sortedScores = [...buckets.keys()].sort((a, b) => a - b)
  for (const score of sortedScores) {
    const arr = buckets.get(score)
    arr.forEach((row, yi) => {
      const meta = scoreToColor(score)
      out.push({
        ...row,
        x: score,
        y: yi,
        r: score > 80 ? 8 : 5,
        fillVar: meta.color,
      })
    })
  }
  return out
}

function DotsTooltip({ active, payload }) {
  if (!active || !payload?.length) return null
  const p = payload[0].payload
  return (
    <div className={tt.wrap}>
      <p className={tt.label}>Identidad</p>
      <p className={tt.value}>{p.usuario || p.nombre_completo || p.id || '—'}</p>
      <p className={tt.label}>Risk score</p>
      <p className={tt.value}>{Math.round(Number(p.score) || 0)}</p>
    </div>
  )
}

function DotShape(props) {
  const { cx, cy, payload, onSelect } = props
  if (cx == null || cy == null || !payload) return null
  return (
    <circle
      cx={cx}
      cy={cy}
      r={payload.r}
      fill={payload.fillVar}
      stroke="var(--base-deep)"
      strokeWidth={1}
      className={styles.dot}
      style={{ cursor: onSelect ? 'pointer' : 'default' }}
      onClick={(e) => {
        e.stopPropagation()
        onSelect?.(payload)
      }}
      onKeyDown={(e) => {
        if (!onSelect) return
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault()
          onSelect(payload)
        }
      }}
      tabIndex={onSelect ? 0 : undefined}
      role={onSelect ? 'button' : undefined}
    />
  )
}

/**
 * Dispersión de scores por identidad; clic abre panel de detalle (F09).
 */
export default function RiskDistributionDots({
  identities = [],
  height = 200,
  className = '',
  onIdentityClick,
}) {
  const openDetailPanel = useStore((s) => s.openDetailPanel)

  const points = useMemo(() => layoutPoints(identities), [identities])
  const maxY = useMemo(() => Math.max(1, ...points.map((p) => p.y), 0), [points])

  const handleSelect = useCallback(
    (row) => {
      const id = row.id ?? row.identidad_id ?? row.ip_asociada
      if (onIdentityClick) onIdentityClick(row)
      else if (id != null) openDetailPanel('identity', id)
    },
    [onIdentityClick, openDetailPanel],
  )

  const border = readCssVar('--base-border') || '#1f2b40'
  const subtle = resolveToken('var(--base-subtle)') || '#6b7fa0'

  const shape = useCallback((p) => <DotShape {...p} onSelect={handleSelect} />, [handleSelect])

  if (points.length === 0) {
    return (
      <div className={`${styles.empty} ${className}`.trim()} style={{ height }}>
        Sin identidades
      </div>
    )
  }

  return (
    <div className={`${styles.wrap} ${className}`.trim()} style={{ width: '100%', height }}>
      <ResponsiveContainer width="100%" height="100%">
        <ScatterChart margin={{ top: 12, right: 12, bottom: 28, left: 8 }}>
          <XAxis
            type="number"
            dataKey="x"
            name="score"
            domain={[0, 100]}
            ticks={[0, 25, 50, 75, 100]}
            tick={{ fill: subtle, fontSize: 11, fontFamily: 'var(--font-data)' }}
            tickLine={false}
            axisLine={{ stroke: border }}
          />
          <YAxis
            type="number"
            dataKey="y"
            domain={[-0.5, maxY + 0.5]}
            hide
            allowDecimals={false}
          />
          <Tooltip
            cursor={{ strokeDasharray: '3 3', stroke: border }}
            content={<DotsTooltip />}
            wrapperStyle={{ outline: 'none' }}
          />
          <Scatter data={points} shape={shape} isAnimationActive={false} />
        </ScatterChart>
      </ResponsiveContainer>
    </div>
  )
}
