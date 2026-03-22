import { useCallback, useEffect, useMemo, useState } from 'react'
import { huntingApi } from '../api/client'
import { useStore } from '../store'
import { flattenHuntResultRows } from '../lib/huntingUtils'
import { HypothesisListItem } from '../components/hunting/HypothesisListItem'
import { ManualHypothesisModal } from '../components/hunting/ManualHypothesisModal'
import { SessionQueriesSection } from '../components/hunting/SessionQueriesSection'
import { SessionResultsVirtualized } from '../components/hunting/SessionResultsVirtualized'
import { SessionConclusionPanel } from '../components/hunting/SessionConclusionPanel'
import styles from './HuntingView.module.css'

export default function HuntingView({ onNavigate }) {
  const setTimelineFocusEventId = useStore((s) => s.setTimelineFocusEventId)

  const [hypotheses, setHypotheses] = useState([])
  const [sessions, setSessions] = useState([])
  const [selectedHypothesis, setSelectedHypothesis] = useState(null)
  const [activeSession, setActiveSession] = useState(null)
  const [loadingList, setLoadingList] = useState(true)
  const [listError, setListError] = useState('')
  const [manualOpen, setManualOpen] = useState(false)
  const [manualBusy, setManualBusy] = useState(false)
  const [runningCount, setRunningCount] = useState(0)
  const [runningHypothesisId, setRunningHypothesisId] = useState(null)
  const [sessionLoadError, setSessionLoadError] = useState('')

  const refreshLists = useCallback(async () => {
    setListError('')
    try {
      const [hRes, sRes] = await Promise.all([
        huntingApi.listHypotheses({ limit: 100 }),
        huntingApi.listSessions({ limit: 40 }),
      ])
      setHypotheses(hRes.data || [])
      setSessions(sRes.data || [])
    } catch (e) {
      setListError(e.message || 'Error cargando hunting')
    } finally {
      setLoadingList(false)
    }
  }, [])

  useEffect(() => {
    refreshLists()
  }, [refreshLists])

  const displayHypothesis = useMemo(() => {
    if (activeSession?.hypothesis) return activeSession.hypothesis
    return selectedHypothesis
  }, [activeSession, selectedHypothesis])

  const resultRows = useMemo(
    () => flattenHuntResultRows(activeSession, displayHypothesis),
    [activeSession, displayHypothesis]
  )

  const openTimeline = useCallback(
    (eventId) => {
      if (!eventId) return
      setTimelineFocusEventId(eventId)
      if (onNavigate) onNavigate('timeline')
    },
    [onNavigate, setTimelineFocusEventId]
  )

  const handleCreateManual = async (text) => {
    setManualBusy(true)
    setListError('')
    try {
      const res = await huntingApi.createHypothesis({ descripcion: text, hunter: 'dashboard_analista' })
      const created = res.data
      if (created) {
        setManualOpen(false)
        await refreshLists()
        setSelectedHypothesis(created)
        setActiveSession(null)
      }
    } catch (e) {
      setListError(e.message || 'No se pudo crear la hipótesis')
    } finally {
      setManualBusy(false)
    }
  }

  const handleInvestigate = async (hyp) => {
    if (!hyp?.id) return
    if (runningCount >= 3) {
      setListError('Máximo 3 sesiones de hunting en ejecución simultánea.')
      return
    }
    setListError('')
    setSessionLoadError('')
    setSelectedHypothesis(hyp)
    setActiveSession(null)
    setRunningHypothesisId(hyp.id)
    setRunningCount((c) => c + 1)
    try {
      const res = await huntingApi.runHunt(hyp.id, 'dashboard_analista')
      const sess = res.data
      if (sess) {
        setActiveSession(sess)
        try {
          const detail = await huntingApi.getSession(sess.id)
          setActiveSession(detail.data || sess)
        } catch {
          setActiveSession(sess)
        }
      }
      await refreshLists()
    } catch (e) {
      setSessionLoadError(e.message || 'Error ejecutando hunt')
    } finally {
      setRunningHypothesisId(null)
      setRunningCount((c) => Math.max(0, c - 1))
    }
  }

  const openSession = async (sid) => {
    setSessionLoadError('')
    try {
      const res = await huntingApi.getSession(sid)
      setActiveSession(res.data)
      if (res.data?.hypothesis) {
        setSelectedHypothesis(res.data.hypothesis)
      }
    } catch (e) {
      setSessionLoadError(e.message || 'No se pudo cargar la sesión')
    }
  }

  const etaHint =
    runningHypothesisId && displayHypothesis
      ? `Tiempo estimado máximo: ~${(displayHypothesis.queries_sugeridas?.length || 1) * 30}s (prioridad baja en MongoDB).`
      : ''

  const showRunningPlaceholder = Boolean(runningHypothesisId && selectedHypothesis?.id === runningHypothesisId)

  return (
    <div className={styles.root}>
      <div className={styles.advancedBadge} role="status">
        Función avanzada — Threat Hunting
      </div>

      <div className={styles.grid}>
        <aside className={styles.left}>
          <div className={styles.leftHeader}>
            <h1 className={styles.title}>Hipótesis</h1>
            <button type="button" className={styles.btnNew} onClick={() => setManualOpen(true)}>
              Nueva hipótesis manual
            </button>
          </div>

          {loadingList && <p className={styles.muted}>Cargando…</p>}
          {listError && <p className={styles.error}>{listError}</p>}

          <div className={styles.hypList}>
            {hypotheses.map((h) => (
              <HypothesisListItem
                key={h.id}
                hypothesis={h}
                selected={selectedHypothesis?.id === h.id}
                onSelect={(hyp) => {
                  setSelectedHypothesis(hyp)
                  setActiveSession(null)
                }}
                onInvestigate={handleInvestigate}
                investigating={runningHypothesisId === h.id}
                disabledInvestigate={runningCount >= 3}
              />
            ))}
          </div>

          <div className={styles.sessionsBlock}>
            <h2 className={styles.subTitle}>Sesiones recientes</h2>
            <ul className={styles.sessionUl}>
              {sessions.map((s) => (
                <li key={s.id}>
                  <button type="button" className={styles.sessionBtn} onClick={() => openSession(s.id)}>
                    <span className={styles.sessionId}>{s.id}</span>
                    <span className={styles.sessionMeta}>
                      {s.estado} · {s.resultados_totales ?? 0} docs
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          </div>
        </aside>

        <section className={styles.right} aria-label="Detalle de sesión">
          {!displayHypothesis && !activeSession && (
            <div className={styles.emptyRight}>
              <p>Elegí una hipótesis o una sesión para ver el detalle de investigación.</p>
            </div>
          )}

          {(displayHypothesis || activeSession) && (
            <>
              <header className={styles.detailHead}>
                <h2 className={styles.detailTitle}>{displayHypothesis?.titulo || 'Sesión de hunting'}</h2>
                {displayHypothesis?.tecnica_mitre && displayHypothesis.tecnica_mitre !== 'T0000' && (
                  <span className={styles.mitreBadge}>{displayHypothesis.tecnica_mitre}</span>
                )}
                <p className={styles.detailDesc}>{displayHypothesis?.descripcion}</p>
              </header>

              {sessionLoadError && <p className={styles.error}>{sessionLoadError}</p>}

              <SessionQueriesSection
                hypothesis={displayHypothesis}
                detalleQueries={activeSession?.detalle_queries}
                runningPlaceholder={showRunningPlaceholder}
                etaHint={showRunningPlaceholder ? etaHint : ''}
              />

              <section className={styles.resultsSection} aria-labelledby="hunt-results-title">
                <h2 id="hunt-results-title" className={styles.sectionHeading}>
                  Resultados (muestra)
                </h2>
                <SessionResultsVirtualized rows={resultRows} onOpenTimeline={openTimeline} />
              </section>

              <SessionConclusionPanel
                conclusion={activeSession?.conclusion}
                onGoTimeline={() => onNavigate?.('timeline')}
              />
            </>
          )}
        </section>
      </div>

      <ManualHypothesisModal
        isOpen={manualOpen}
        onClose={() => setManualOpen(false)}
        onSubmit={handleCreateManual}
        busy={manualBusy}
      />
    </div>
  )
}
