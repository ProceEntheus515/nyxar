import React, { Suspense, useState, useEffect } from 'react'
import { useWebSocket } from './hooks/useWebSocket'
import { useStore } from './store'
import Skeleton from './components/ui/Skeleton'
import StatusDot from './components/ui/StatusDot'
import { Sidebar } from './components/layout/Sidebar'

import { MOCK_DATA } from './lib/mock'

const TAB_TITLES = {
  map: 'NYXAR — Red',
  timeline: 'NYXAR — Timeline',
  identities: 'NYXAR — Identidades',
  hunting: 'NYXAR — Hunting',
  response: 'NYXAR — Respuestas',
  reports: 'NYXAR — Reportes',
  ceo: 'NYXAR — Vista Ejecutiva',
  health: 'NYXAR — Sistema',
}

const NetworkMap = React.lazy(() => import('./views/NetworkMap'))
const Timeline = React.lazy(() => import('./views/Timeline'))
const Identities = React.lazy(() => import('./views/Identities'))
const HuntingView = React.lazy(() => import('./views/HuntingView'))
const AttackInjector = React.lazy(() => import('./views/AttackInjector'))

function LoadingView() {
  return (
    <div className="w-full h-full flex flex-col gap-4 p-4">
      <Skeleton height="60px" />
      <div className="flex-1 flex gap-4">
        <Skeleton width="300px" height="100%" />
        <Skeleton width="100%" height="100%" />
      </div>
    </div>
  )
}

export default function App() {
  useWebSocket()

  const { isLabMode, identities, stats, setInitialState } = useStore()
  const [activeTab, setActiveTab] = useState('map')

  useEffect(() => {
    setInitialState(MOCK_DATA)
  }, [])

  useEffect(() => {
    document.title = TAB_TITLES[activeTab] || 'NYXAR'
  }, [activeTab])

  return (
    <div className="min-h-screen h-screen bg-[var(--bg-main)] text-[var(--text-main)] flex overflow-hidden">
      <Sidebar activeTab={activeTab} onTabChange={setActiveTab} />

      <div className="flex-1 flex flex-col min-w-0 min-h-0">
        <header className="h-[60px] bg-[#161B22] border-b border-[var(--border-default)] flex items-center justify-between px-6 shrink-0 z-40 shadow-md">
          <div className="flex items-center gap-6">
            <div className="flex flex-col items-start">
              <span className="text-[10px] text-[var(--text-sec)] font-mono uppercase">NYXAR</span>
              <span className="text-xs text-[var(--color-primary)] uppercase tracking-widest font-mono">
                SOC Central Dashboard
              </span>
            </div>
          </div>

          <div className="flex items-center gap-6">
            <div className="flex flex-col items-end">
              <span className="text-[10px] text-[var(--text-sec)] font-mono uppercase">Eventos/min</span>
              <span className="text-sm font-bold">{stats?.eventos_por_min || 0}</span>
            </div>
            <div className="flex flex-col items-end">
              <span className="text-[10px] text-[var(--text-sec)] font-mono uppercase">Alertas Activas</span>
              <span className="text-sm font-bold text-[var(--color-critical)]">{stats?.alertas_abiertas || 0}</span>
            </div>
            <div className="flex items-center gap-2 border-l border-[#21262D] pl-4">
              <StatusDot status="online" />
              <span className="text-xs text-[var(--text-sec)]">WS Conectado</span>
            </div>
          </div>
        </header>

        <main className="flex-1 overflow-hidden relative p-6 min-h-0">
          <Suspense fallback={<LoadingView />}>
            {activeTab === 'map' && <NetworkMap />}
            {activeTab === 'timeline' && <Timeline />}
            {activeTab === 'identities' && <Identities />}
            {activeTab === 'hunting' && <HuntingView onNavigate={setActiveTab} />}
          </Suspense>
        </main>

        <Suspense fallback={null}>
          <AttackInjector isLabMode={isLabMode || true} identities={identities} />
        </Suspense>
      </div>
    </div>
  )
}
