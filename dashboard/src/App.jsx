import React, { Suspense, useState, useEffect } from 'react';
import { useWebSocket } from './hooks/useWebSocket';
import { useStore } from './store';
import Skeleton from './components/ui/Skeleton';
import StatusDot from './components/ui/StatusDot';

import { MOCK_DATA } from './lib/mock';

// Lazy load views para performance
const NetworkMap = React.lazy(() => import('./views/NetworkMap'));
const Timeline = React.lazy(() => import('./views/Timeline'));
const Identities = React.lazy(() => import('./views/Identities'));
const AttackInjector = React.lazy(() => import('./views/AttackInjector'));

function LoadingView() {
  return (
    <div className="w-full h-full flex flex-col gap-4 p-4">
      <Skeleton height="60px" />
      <div className="flex-1 flex gap-4">
        <Skeleton width="300px" height="100%" />
        <Skeleton width="100%" height="100%" />
      </div>
    </div>
  );
}

export default function App() {
  // Inicializamos y atamos el Websocket Singleton al ciclo de vida global
  useWebSocket();
  
  const { isLabMode, identities, stats, setInitialState } = useStore();
  const [activeTab, setActiveTab] = useState('map');

  // Request inicial status o simulacion (opcional)
  useEffect(() => {
    // Inject Mock initial data instantly to allow rendering without backend!
    setInitialState(MOCK_DATA);
  }, []);

  return (
    <div className="min-h-screen bg-[var(--bg-main)] text-[var(--text-main)] flex flex-col overflow-hidden">
      {/* Header Corporativo SOC */}
      <header className="h-[60px] bg-[#161B22] border-b border-[var(--border-default)] flex items-center justify-between px-6 shrink-0 z-50 shadow-md">
        <div className="flex items-center gap-4">
          <div className="w-8 h-8 rounded shrink-0 bg-gradient-to-br from-[var(--color-primary)] to-[var(--color-info)] flex items-center justify-center font-bold text-black border shadow-[0_0_10px_var(--color-primary)]">
            CP
          </div>
          <div>
            <h1 className="font-bold text-[15px] tracking-wide m-0 leading-tight">CyberPulse LATAM</h1>
            <p className="text-[10px] text-[var(--color-primary)] uppercase tracking-widest font-mono">SOC Central Dashboard</p>
          </div>
        </div>

        <nav className="flex gap-1 h-full pt-4">
          <button 
            onClick={() => setActiveTab('map')}
            className={`px-4 pb-3 text-sm font-medium border-b-2 transition-colors ${activeTab === 'map' ? 'border-[var(--color-primary)] text-white' : 'border-transparent text-[var(--text-sec)] hover:text-white'}`}
          >
            Network Graph
          </button>
          <button 
            onClick={() => setActiveTab('timeline')}
            className={`px-4 pb-3 text-sm font-medium border-b-2 transition-colors ${activeTab === 'timeline' ? 'border-[var(--color-primary)] text-white' : 'border-transparent text-[var(--text-sec)] hover:text-white'}`}
          >
            Live Events Timeline
          </button>
          <button 
            onClick={() => setActiveTab('identities')}
            className={`px-4 pb-3 text-sm font-medium border-b-2 transition-colors ${activeTab === 'identities' ? 'border-[var(--color-primary)] text-white' : 'border-transparent text-[var(--text-sec)] hover:text-white'}`}
          >
            Risk Identities
          </button>
        </nav>

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

      {/* Area de Contenido */}
      <main className="flex-1 overflow-hidden relative p-6">
        <Suspense fallback={<LoadingView />}>
           {activeTab === 'map' && <NetworkMap />}
           {activeTab === 'timeline' && <Timeline />}
           {activeTab === 'identities' && <Identities />}
        </Suspense>
      </main>

      {/* Inyector Flotante condicional */}
      <Suspense fallback={null}>
         <AttackInjector isLabMode={isLabMode || true} identities={identities} /> {/* Forzado provisional hasta conectar vars reales de entorno */}
      </Suspense>
    </div>
  );
}
