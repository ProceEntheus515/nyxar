import { useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import DataChip from '../ui/DataChip'
import Badge from '../ui/Badge'
import RiskGauge from '../ui/RiskGauge'
import AreaBadge from '../ui/AreaBadge'
import SourceTag from '../ui/SourceTag'
import { scoreToColor, normalizeSourceKey } from '../../lib/colors'
import { internoNodeId } from '../../lib/networkMap/internalGraph'
import { useStore } from '../../store'
import styles from './EventDetailContent.module.css'

function isProbablyIp(s) {
  const v = String(s || '').trim()
  if (!v) return false
  return /^(\d{1,3}\.){3}\d{1,3}$/.test(v)
}

function formatExactTs(iso) {
  try {
    const d = new Date(iso)
    return d.toLocaleString('es', {
      dateStyle: 'medium',
      timeStyle: 'medium',
    })
  } catch {
    return String(iso || '—')
  }
}

function malwareTagsList(enrichment) {
  const e = enrichment || {}
  const raw = e.tags_malware || e.malware_tags || e.malware || e.tags
  if (Array.isArray(raw)) return raw.map(String).filter(Boolean)
  if (typeof raw === 'string' && raw.trim()) return [raw.trim()]
  return []
}

/**
 * Contenido del panel lateral para un evento del Timeline (F08).
 */
export default function EventDetailContent({ eventId }) {
  const navigate = useNavigate()
  const events = useStore((s) => s.events)
  const identities = useStore((s) => s.identities)
  const incidents = useStore((s) => s.incidents)
  const alerts = useStore((s) => s.alerts)
  const openDetailPanel = useStore((s) => s.openDetailPanel)
  const requestMapFocus = useStore((s) => s.requestMapFocus)

  const event = useMemo(
    () => (events || []).find((ev) => String(ev.id) === String(eventId)),
    [events, eventId],
  )

  const nodeId = event ? internoNodeId(event) : null
  const identity = nodeId ? identities[nodeId] : null

  const relatedIncident = useMemo(
    () => (incidents || []).find((inc) => String(inc.evento_original_id) === String(eventId)),
    [incidents, eventId],
  )

  const relatedAlert = useMemo(
    () => (alerts || []).find((al) => String(al.evento_original_id) === String(eventId)),
    [alerts, eventId],
  )

  const similarCount = useMemo(() => {
    if (!event || !nodeId) return 0
    const src = normalizeSourceKey(event.source)
    const cutoff = Date.now() - 24 * 3600000
    return (events || []).filter((ev) => {
      if (String(ev.id) === String(event.id)) return false
      if (internoNodeId(ev) !== nodeId) return false
      if (normalizeSourceKey(ev.source) !== src) return false
      const t = new Date(ev.timestamp).getTime()
      return Number.isFinite(t) && t >= cutoff
    }).length
  }, [events, event, eventId, nodeId])

  if (!event) {
    return (
      <p className={styles.muted}>
        No se encontró el evento en el buffer (pudo haber salido del anillo de 500).
      </p>
    )
  }

  const enr = event.enrichment || {}
  const riskEvent = Number(enr.risk_score)
  const riskIdentity = identity != null ? Number(identity.risk_score) : NaN
  const riskShown = Number.isFinite(riskIdentity) ? riskIdentity : riskEvent
  const hasRiskShown = Number.isFinite(riskShown)
  const { label: repLabel } = hasRiskShown ? scoreToColor(riskShown) : { label: '—' }

  const externoVal = event.externo?.valor || '—'
  const chipType = isProbablyIp(externoVal) ? 'ip' : 'domain'

  const pais = enr.pais || enr.country || '—'
  const asn = enr.asn != null ? (typeof enr.as === 'string' ? enr.as : `AS${enr.asn}`) : '—'
  const threatSrc = enr.threat_intel || enr.fuente_threat || enr.intel_source || '—'
  const tags = malwareTagsList(enr)

  const vtUrl = isProbablyIp(externoVal)
    ? `https://www.virustotal.com/gui/ip-address/${encodeURIComponent(externoVal)}`
    : `https://www.virustotal.com/gui/domain/${encodeURIComponent(externoVal)}`
  const abuseUrl =
    isProbablyIp(externoVal) && externoVal !== '—'
      ? `https://www.abuseipdb.com/check/${encodeURIComponent(externoVal)}`
      : null

  const userLabel = event.interno?.id_usuario || event.interno?.ip || '—'
  const area = event.interno?.area || 'Desconocido'
  const hostname = identity?.hostname || identity?.dispositivo || '—'

  const onMap = () => {
    if (!nodeId) return
    requestMapFocus(nodeId)
    navigate('/map')
  }

  return (
    <div className={styles.root}>
      <div>
        <h3 className={styles.sectionTitle}>Resumen</h3>
        <div className={styles.summaryHead}>
          <SourceTag source={event.source} />
          <span className={styles.metaRow}>{event.tipo || event.type || 'evento'}</span>
        </div>
        <p className={styles.metaRow}>{formatExactTs(event.timestamp)}</p>
      </div>

      <div>
        <h3 className={styles.sectionTitle}>Identidad involucrada</h3>
        <div className={styles.identityBlock}>
          <span className={styles.identityLine}>
            <span className={styles.userStrong}>{userLabel}</span>
          </span>
          <AreaBadge area={area} />
          <span className={styles.identityLine}>IP: {event.interno?.ip || nodeId || '—'}</span>
          <span className={styles.identityLine}>Hostname: {hostname}</span>
          <div className={styles.actions}>
            <button type="button" className={styles.btn} onClick={onMap} disabled={!nodeId}>
              Ver en mapa
            </button>
            {nodeId ? (
              <button
                type="button"
                className={`${styles.btn} ${styles.btnGhost}`.trim()}
                onClick={() => openDetailPanel('identity', nodeId)}
              >
                Ver perfil completo
              </button>
            ) : null}
          </div>
        </div>
      </div>

      <div>
        <h3 className={styles.sectionTitle}>Valor externo</h3>
        <DataChip value={externoVal} type={chipType} truncate={chipType === 'domain'} copyable />
      </div>

      <div>
        <h3 className={styles.sectionTitle}>Enrichment</h3>
        <dl className={styles.grid}>
          <dt>Reputación</dt>
          <dd>
            {hasRiskShown ? (
              <Badge variant={riskShown >= 80 ? 'critical' : riskShown >= 60 ? 'high' : 'medium'} size="sm">
                {repLabel} ({Math.round(riskShown)})
              </Badge>
            ) : (
              '—'
            )}
          </dd>
          <dt>País</dt>
          <dd>{pais}</dd>
          <dt>ASN</dt>
          <dd>{asn}</dd>
          <dt>Fuente threat intel</dt>
          <dd>{threatSrc}</dd>
          {tags.length > 0 ? (
            <>
              <dt>Tags malware</dt>
              <dd>{tags.join(', ')}</dd>
            </>
          ) : null}
        </dl>
        <div className={styles.links}>
          {externoVal && externoVal !== '—' ? (
            <a className={styles.extLink} href={vtUrl} target="_blank" rel="noreferrer noopener">
              VirusTotal
            </a>
          ) : null}
          {abuseUrl ? (
            <a className={styles.extLink} href={abuseUrl} target="_blank" rel="noreferrer noopener">
              AbuseIPDB
            </a>
          ) : null}
        </div>
      </div>

      <div>
        <h3 className={styles.sectionTitle}>Contexto de la identidad</h3>
        <div className={styles.riskRow}>
          {hasRiskShown ? <RiskGauge score={riskShown} size="sm" /> : null}
          <p className={styles.muted}>
            Este usuario generó {similarCount} evento{similarCount === 1 ? '' : 's'} similar
            {similarCount === 1 ? '' : 'es'} en las últimas 24h.
          </p>
        </div>
      </div>

      {relatedIncident ? (
        <div>
          <h3 className={styles.sectionTitle}>Incidente relacionado</h3>
          <div className={styles.incidentCard}>
            <p className={styles.incidentTitle}>{relatedIncident.descripcion || 'Incidente'}</p>
            <p className={styles.incidentMeta}>
              {relatedIncident.severidad || '—'} · {relatedIncident.estado || '—'}
            </p>
            <div className={styles.actions}>
              <button
                type="button"
                className={styles.btn}
                onClick={() => openDetailPanel('incident', relatedIncident.id)}
              >
                Ver incidente
              </button>
            </div>
          </div>
        </div>
      ) : relatedAlert ? (
        <div>
          <h3 className={styles.sectionTitle}>Alerta vinculada</h3>
          <div className={styles.incidentCard}>
            <p className={styles.incidentTitle}>{relatedAlert.titulo || 'Alerta'}</p>
            <p className={styles.incidentMeta}>
              {relatedAlert.severidad || relatedAlert.tipo || '—'}
            </p>
          </div>
        </div>
      ) : null}
    </div>
  )
}
