import { useCallback, useEffect, useMemo, useState } from 'react'
import { useStore } from '../store'
import { responseApi } from '../api/client'
import ResponseProposalCard from '../components/responses/ResponseProposalCard'
import EmptyState from '../components/ui/EmptyState'
import styles from './ResponseView.module.css'

function isPending(p) {
  return String(p?.estado || '') === 'pendiente_aprobacion'
}

export default function ResponseView() {
  const proposals = useStore((s) => s.proposals)
  const setProposals = useStore((s) => s.setProposals)
  const removeProposal = useStore((s) => s.removeProposal)

  const [loadError, setLoadError] = useState(null)
  const [busyId, setBusyId] = useState(null)

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        const res = await responseApi.getProposals({
          estado: 'pendiente_aprobacion',
          limit: 50,
        })
        const rows = Array.isArray(res?.data) ? res.data : []
        if (cancelled) return
        const prev = useStore.getState().proposals
        const byId = new Map()
        for (const x of prev) {
          if (x?.id) byId.set(x.id, x)
        }
        for (const row of rows) {
          if (row?.id) byId.set(row.id, row)
        }
        setProposals(Array.from(byId.values()))
        setLoadError(null)
      } catch (e) {
        if (!cancelled) {
          setLoadError(e?.message || 'No se pudieron cargar las propuestas')
          console.error(e)
        }
      }
    })()
    return () => {
      cancelled = true
    }
  }, [setProposals])

  const pendientes = useMemo(() => proposals.filter(isPending), [proposals])

  const handleApprove = useCallback(
    async (proposalId, comentario) => {
      setBusyId(proposalId)
      try {
        await responseApi.approve(proposalId, comentario || '')
        removeProposal(proposalId)
      } catch (e) {
        console.error(e)
      } finally {
        setBusyId(null)
      }
    },
    [removeProposal],
  )

  const handleReject = useCallback(
    async (proposalId, motivo) => {
      setBusyId(proposalId)
      try {
        await responseApi.reject(proposalId, motivo)
        removeProposal(proposalId)
      } catch (e) {
        console.error(e)
      } finally {
        setBusyId(null)
      }
    },
    [removeProposal],
  )

  return (
    <div className={styles.wrap}>
      <header className={styles.header}>
        <h1 className={styles.title}>Respuestas automatizadas</h1>
        <p className={styles.sub}>
          Propuestas SOAR pendientes de aprobación. Los eventos en tiempo real llegan por WebSocket
          (canal <code className={styles.code}>response_proposal</code>).
        </p>
      </header>

      {loadError ? <p className={styles.err}>{loadError}</p> : null}

      {pendientes.length === 0 ? (
        <EmptyState
          icon="◇"
          title="Sin propuestas pendientes"
          description="Cuando el motor auto_response genere un plan, aparecerá aquí y en el badge del menú."
        />
      ) : (
        <ul className={styles.list}>
          {pendientes.map((p) => (
            <li key={p.id} className={styles.li}>
              <ResponseProposalCard
                proposal={p}
                onApprove={handleApprove}
                onReject={handleReject}
                busyId={busyId}
              />
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
