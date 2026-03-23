import React, { Suspense, useEffect } from 'react'
import { BrowserRouter, Routes, Route, Navigate, useNavigate } from 'react-router-dom'
import { useWebSocket } from './hooks/useWebSocket'
import { useStore } from './store'
import Skeleton from './components/ui/Skeleton'
import AppShell from './components/layout/AppShell'

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

  return (
    <BrowserRouter>
      <AppRoutes />
    </BrowserRouter>
  )
}
