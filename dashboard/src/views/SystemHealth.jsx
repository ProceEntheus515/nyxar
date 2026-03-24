import { useEffect } from 'react'
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from 'recharts'
import { useStore } from '../store'
import { healthApi } from '../api/client'
import HealthCard from '../components/health/HealthCard'
import styles from './SystemHealth.module.css'

const DETAIL_KEY = import.meta.env.VITE_HEALTH_DETAIL_KEY || ''

const COMP_ORDER = ['redis', 'mongodb', 'pipeline']
const SVC_ORDER = ['collector', 'enricher', 'correlator', 'ai_analyst', 'notifier', 'api']
const API_ORDER = ['abuseipdb', 'otx', 'misp', 'anthropic']

const LABELS = {
  redis: 'Redis',
  mongodb: 'MongoDB',
  pipeline: 'Pipeline',
  collector: 'Collector',
  enricher: 'Enricher',
  correlator: 'Correlator',
  ai_analyst: 'AI Analyst',
  notifier: 'Notifier',
  api: 'API',
  abuseipdb: 'AbuseIPDB',
  otx: 'AlienVault OTX',
  misp: 'MISP',
  anthropic: 'Claude API',
}

function pickComponents(map, order) {
  if (!map) return []
  return order.map((k) => (map[k] ? { key: k, h: map[k] } : null)).filter(Boolean)
}

export default function SystemHealth() {
  const { healthReport, healthThroughput, setHealthReport } = useStore()

  useEffect(() => {
    if (!DETAIL_KEY) return
    let cancelled = false
    const load = async () => {
      try {
        const data = await healthApi.getDetail(DETAIL_KEY)
        if (!cancelled && data) setHealthReport(data)
      } catch {
        /* esperamos actualización por WebSocket */
      }
    }
    load()
    return () => {
      cancelled = true
    }
  }, [setHealthReport])

  const comp = pickComponents(healthReport?.componentes, COMP_ORDER)
  const svc = pickComponents(healthReport?.servicios, SVC_ORDER)
  const apis = pickComponents(healthReport?.apis, API_ORDER)

  const chartData = (healthThroughput || []).map((row) => ({
    t: row.minute?.slice(11, 16) || row.minute,
    n: row.count ?? 0,
  }))

  return (
    <div className={styles.wrap}>
      <p className={styles.summary}>
        <strong>{healthReport?.estado_general || 'sin datos'}</strong>
        {healthReport?.resumen ? ` — ${healthReport.resumen}` : ''}
      </p>
      {!DETAIL_KEY ? (
        <p className={styles.hint}>
          Opcional: definí VITE_HEALTH_DETAIL_KEY y HEALTH_DETAIL_API_KEY en API para refrescar
          detalle vía HTTP además del WebSocket.
        </p>
      ) : null}

      <h2 className={styles.sectionTitle}>Infraestructura</h2>
      <div className={styles.grid}>
        {comp.map(({ key, h }) => (
          <HealthCard key={key} titulo={LABELS[key] || key} health={h} />
        ))}
      </div>

      <h2 className={styles.sectionTitle}>Servicios</h2>
      <div className={styles.grid}>
        {svc.map(({ key, h }) => (
          <HealthCard key={key} titulo={LABELS[key] || key} health={h} />
        ))}
      </div>

      <h2 className={styles.sectionTitle}>APIs externas</h2>
      <div className={styles.grid}>
        {apis.map(({ key, h }) => (
          <HealthCard key={key} titulo={LABELS[key] || key} health={h} />
        ))}
      </div>

      <div className={styles.chartWrap}>
        <h3 className={styles.chartTitle}>Eventos por minuto (últimas 2 h)</h3>
        <div className={styles.chartInner}>
          <ResponsiveContainer
            width="100%"
            height="100%"
            minWidth={0}
            minHeight={220}
            initialDimension={{ width: 640, height: 280 }}
          >
          <LineChart data={chartData} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
            <CartesianGrid stroke="var(--base-border)" strokeDasharray="3 3" />
            <XAxis dataKey="t" tick={{ fill: 'var(--base-subtle)', fontSize: 10 }} />
            <YAxis tick={{ fill: 'var(--base-subtle)', fontSize: 10 }} allowDecimals={false} />
            <Tooltip
              contentStyle={{
                background: 'var(--base-surface)',
                border: '1px solid var(--base-border-strong)',
              }}
              labelStyle={{ color: 'var(--base-text)' }}
            />
            <Line type="monotone" dataKey="n" stroke="var(--color-primary)" dot={false} strokeWidth={2} />
          </LineChart>
        </ResponsiveContainer>
        </div>
      </div>
    </div>
  )
}
