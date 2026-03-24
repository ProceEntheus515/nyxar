import React, { Suspense, useEffect } from 'react'
import { BrowserRouter, Routes, Route, Navigate, useNavigate } from 'react-router-dom'
import { useWebSocket } from './hooks/useWebSocket'
import { useStore } from './store'
import Skeleton from './components/ui/Skeleton'
import AppShell from './components/layout/AppShell'
import { eventsApi, identitiesApi, incidentsApi, aiApi } from './api/client'

import { isDevDataEnabled } from './lib/devData'
import { buildDevMockInitialState } from './lib/mock'

const NetworkMap = React.lazy(() => import('./views/NetworkMap'))
const Timeline = React.lazy(() => import('./views/Timeline'))
const Identities = React.lazy(() => import('./views/Identities'))
const HuntingView = React.lazy(() => import('./views/HuntingView'))
const SystemHealth = React.lazy(() => import('./views/SystemHealth'))
const RoutePlaceholder = React.lazy(() => import('./views/RoutePlaceholder'))
const CeoView = React.lazy(() => import('./views/CeoView'))

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

function AppRoutes() {
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
      } catch (err) {
        console.error('Error cargando estado inicial:', err)
      }
    }

    loadInitialState()
  }, [])

  return (
    <>
      <Suspense fallback={<LoadingView />}>
        <Routes>
          <Route element={<AppShell />}>
            <Route path="/" element={<Navigate to="/map" replace />} />
            <Route path="map" element={<NetworkMap />} />
            <Route path="timeline" element={<Timeline />} />
            <Route path="identities" element={<Identities />} />
            <Route path="hunting" element={<HuntingViewRoute />} />
            <Route path="health" element={<SystemHealth />} />
            <Route
              path="responses"
              element={
                <RoutePlaceholder
                  title="Respuestas"
                  description="Propuestas de respuesta y playbooks automatizados. Pantalla en construcción."
                />
              }
            />
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
    </>
  )
}

export default function App() {
  useWebSocket()

  useEffect(() => {
    if (!import.meta.env.DEV) return
    const t = setTimeout(() => {
      const state = useStore.getState()
      console.group('=== Verificación del Store (I07) ===')
      console.log('Conectado (WS):', state.wsConnected)
      console.log('Eventos cargados:', state.events.length)
      console.log('Identidades cargadas:', Object.keys(state.identities).length)
      console.log('Incidentes:', state.incidents.length)
      console.log('AI Memos:', state.aiMemos.length)
      console.log('Lab mode:', state.isLabMode)

      if (state.events.length === 0) {
        console.warn('Sin eventos: revisar WebSocket y GET /events')
      }
      if (Object.keys(state.identities).length === 0) {
        console.warn('Sin identidades: revisar GET /identities')
      }
      console.groupEnd()
    }, 3000)
    return () => clearTimeout(t)
  }, [])

  return (
    <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <AppRoutes />
    </BrowserRouter>
  )
}
