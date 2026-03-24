import React, { Suspense, useEffect } from 'react'
import { Routes, Route, Navigate, useNavigate } from 'react-router-dom'
import { useStore } from '../../store'
import Skeleton from '../ui/Skeleton'
import AppShell from '../layout/AppShell'
import { eventsApi, identitiesApi, incidentsApi, aiApi, responseApi } from '../../api/client'

import { isDevDataEnabled } from '../../lib/devData'
import { buildDevMockInitialState } from '../../lib/mock'

const NetworkMap = React.lazy(() => import('../../views/NetworkMap'))
const Timeline = React.lazy(() => import('../../views/Timeline'))
const Identities = React.lazy(() => import('../../views/Identities'))
const HuntingView = React.lazy(() => import('../../views/HuntingView'))
const SystemHealth = React.lazy(() => import('../../views/SystemHealth'))
const RoutePlaceholder = React.lazy(() => import('../../views/RoutePlaceholder'))
const CeoView = React.lazy(() => import('../../views/CeoView'))
const ResponseView = React.lazy(() => import('../../views/ResponseView'))

function LoadingView() {
  return (
    <div className="w-full h-full flex flex-col gap-4">
      <Skeleton height="60px" />
      <div className="flex-1 flex gap-4">
        <Skeleton width="300px" height="100%" />
        <Skeleton width="100%" height="100%" />
      </div>
    </div>
  )
}

function HuntingViewRoute() {
  const navigate = useNavigate()
  return <HuntingView onNavigate={(tab) => navigate(`/${tab}`)} />
}

export default function AppRoutes() {
  const { setInitialState } = useStore()

  useEffect(() => {
    if (isDevDataEnabled) setInitialState(buildDevMockInitialState())
  }, [setInitialState])

  useEffect(() => {
    if (isDevDataEnabled) return

    async function loadInitialState() {
      try {
        const eventsRes = await eventsApi.getAll({ limit: 50 })
        const eventsList = Array.isArray(eventsRes?.data) ? eventsRes.data : []
        useStore.getState().addEvents(eventsList)

        const identitiesRes = await identitiesApi.getAll()
        const identitiesList = Array.isArray(identitiesRes?.data) ? identitiesRes.data : []
        useStore.getState().setIdentities(identitiesList)

        const incidentsRes = await incidentsApi.getAll({ estado: 'abierto' })
        const incidentsList = Array.isArray(incidentsRes?.data) ? incidentsRes.data : []
        useStore.getState().setIncidents(incidentsList)

        const memosRes = await aiApi.getMemos()
        const memosList = Array.isArray(memosRes?.data) ? memosRes.data : []
        useStore.getState().setAiMemos(memosList)

        const propRes = await responseApi.getProposals({
          estado: 'pendiente_aprobacion',
          limit: 50,
        })
        const propList = Array.isArray(propRes?.data) ? propRes.data : []
        useStore.getState().setProposals(propList)
      } catch (err) {
        console.error('Error cargando estado inicial:', err)
      }
    }

    loadInitialState()
  }, [])

  return (
    <Suspense fallback={<LoadingView />}>
      <Routes>
        <Route element={<AppShell />}>
          <Route path="/" element={<Navigate to="/map" replace />} />
          <Route path="map" element={<NetworkMap />} />
          <Route path="timeline" element={<Timeline />} />
          <Route path="identities" element={<Identities />} />
          <Route path="hunting" element={<HuntingViewRoute />} />
          <Route path="health" element={<SystemHealth />} />
          <Route path="responses" element={<ResponseView />} />
          <Route
            path="reports"
            element={
              <RoutePlaceholder
                title="Reportes"
                description="Informes exportables y programados. Pantalla en construcción."
              />
            }
          />
          <Route path="ceo" element={<CeoView />} />
        </Route>
      </Routes>
    </Suspense>
  )
}
