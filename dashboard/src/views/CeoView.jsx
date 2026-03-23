import { useCallback, useEffect, useRef, useState } from 'react'
import { useStore } from '../store'
import { ceoApi } from '../api/client'
import { normalizeCeoFromApiPayload } from '../lib/ceoViewModel'
import { formatRelativeTimeEs } from '../lib/relativeTimeEs'
import EmptyState from '../components/ui/EmptyState'
import CeoViewHeader from '../components/ceo/CeoViewHeader'
import CeoTrafficLight from '../components/ceo/CeoTrafficLight'
import CeoAnalysisNarrative from '../components/ceo/CeoAnalysisNarrative'
import CeoRecommendedAction from '../components/ceo/CeoRecommendedAction'
import CeoHistoryList from '../components/ceo/CeoHistoryList'
import styles from './CeoView.module.css'

const PROGRESS_TICK_MS = 80
const ESTIMATED_MS = 8000
const MAX_BEFORE_DONE = 90

export default function CeoView() {
  const ceoAnalyses = useStore((s) => s.ceoAnalyses)
  const addCeoAnalysis = useStore((s) => s.addCeoAnalysis)

  const [loading, setLoading] = useState(false)
  const [progress, setProgress] = useState(0)
  const [error, setError] = useState(null)
  const [expandedHistoryId, setExpandedHistoryId] = useState(null)

  const loadingRef = useRef(false)

  const latest = ceoAnalyses?.[0]
  const historySlice = Array.isArray(ceoAnalyses) ? ceoAnalyses.slice(0, 5) : []

  const runRefresh = useCallback(async () => {
    setError(null)
    loadingRef.current = true
    setLoading(true)
    setProgress(0)

    const started = Date.now()
    const intervalId = window.setInterval(() => {
      if (!loadingRef.current) return
      const elapsed = Date.now() - started
      if (elapsed < ESTIMATED_MS) {
        setProgress(Math.min(MAX_BEFORE_DONE, (elapsed / ESTIMATED_MS) * MAX_BEFORE_DONE))
      } else {
        setProgress(MAX_BEFORE_DONE)
      }
    }, PROGRESS_TICK_MS)

    try {
      const body = await ceoApi.requestCeoView()
      const raw = body?.data ?? body
      const normalized = normalizeCeoFromApiPayload(raw)
      addCeoAnalysis(normalized)
      setProgress(100)
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'No se pudo generar el análisis.'
      setError(msg)
    } finally {
      loadingRef.current = false
      window.clearInterval(intervalId)
      setLoading(false)
      window.setTimeout(() => setProgress(0), 400)
    }
  }, [addCeoAnalysis])

  useEffect(() => {
    return () => {
      loadingRef.current = false
    }
  }, [])

  const lastRelative = latest?.created_at ? formatRelativeTimeEs(latest.created_at) : ''

  return (
    <div className={styles.page}>
      <div className={styles.intro}>
        <h1 className={styles.title}>Resumen para dirección</h1>
        <p className={styles.lead}>
          Lectura breve del estado de la organización, sin detalle técnico. Pensada para decidir si hace
          falta profundizar con el equipo de seguridad.
        </p>

        <CeoViewHeader
          loading={loading}
          progress={progress}
          lastIso={latest?.created_at}
          lastRelativeLabel={lastRelative}
          onRefresh={runRefresh}
        />

        {error ? <p className={styles.error}>{error}</p> : null}
      </div>

      {!latest ? (
        <EmptyState
          icon="◇"
          title="Sin análisis todavía"
          description="Pulsa «Actualizar análisis» para generar un texto claro con la postura actual. Si el servidor no está disponible, activá datos de demostración en desarrollo."
          action={
            <button type="button" className={styles.emptyBtn} onClick={runRefresh} disabled={loading}>
              Generar primer análisis
            </button>
          }
        />
      ) : (
        <div className={styles.bodyGrid}>
          <div className={styles.colStatus}>
            <CeoTrafficLight
              semaforo={latest.semaforo}
              headline={latest.headline}
              subline={latest.subline}
            />
            <CeoRecommendedAction text={latest.accion_inmediata} />
          </div>
          <div className={styles.colRead}>
            <CeoAnalysisNarrative paragraphs={latest.paragraphs} />
            <CeoHistoryList
              analyses={historySlice}
              expandedId={expandedHistoryId}
              onExpand={setExpandedHistoryId}
            />
          </div>
        </div>
      )}
    </div>
  )
}
