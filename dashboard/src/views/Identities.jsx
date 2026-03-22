import React, { useState } from 'react';
import { useStore } from '../store';
import Card from '../components/ui/Card';
import RiskBadge from '../components/ui/RiskBadge';
import AreaBadge from '../components/ui/AreaBadge';
import MonoText from '../components/ui/MonoText';
import StatusDot from '../components/ui/StatusDot';
import { scoreToSeverity } from '../lib/utils';
import { LineChart, Line, ResponsiveContainer, YAxis } from 'recharts';

export default function Identities() {
  const { identities } = useStore();
  const [selectedId, setSelectedId] = useState(null);

  // Ordenar identidades por risk_score
  const sortedIdentities = Object.values(identities || {}).sort((a, b) => {
    return (b.risk_score || 0) - (a.risk_score || 0);
  });

  const getInitials = (nombre) => {
    if (!nombre) return '?';
    return nombre.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase();
  };

  const isActive = (lastSeenISO) => {
    if (!lastSeenISO) return false;
    const diff = (new Date() - new Date(lastSeenISO)) / 1000 / 60; // mins
    return diff < 30;
  };

  // Mock histórico si no vino del backend real aún
  const getMockHistory = (score) => {
    return Array.from({ length: 24 }).map((_, i) => ({
      val: Math.max(0, score - Math.floor(Math.random() * 20))
    }));
  };

  return (
    <div className="h-full flex gap-4 w-full">
      <div className={`flex-1 transition-all duration-300 ${selectedId ? 'w-2/3' : 'w-full'}`}>
        <h2 className="text-xl font-semibold text-white mb-4">Risk Identities Table</h2>
        
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {sortedIdentities.map(id => {
            const hasRaised = id.delta_2h > 0;
            const history = id.score_history_24h || getMockHistory(id.risk_score || 0);
            
            return (
              <Card 
                key={id.id} 
                className={`p-4 cursor-pointer hover:border-[var(--color-primary)] transition-all ${selectedId === id.id ? 'border-[var(--color-primary)] shadow-[0_0_15px_-5px_var(--color-primary)]' : ''}`}
                onClick={() => setSelectedId(id.id)}
              >
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-full bg-[#21262D] flex items-center justify-center font-bold text-white shadow-inner">
                      {getInitials(id.nombre_completo)}
                    </div>
                    <div>
                      <h4 className="font-semibold text-[15px] leading-tight text-white flex items-center gap-2">
                        {id.nombre_completo || 'Agente Anónimo'}
                        <StatusDot status={isActive(id.last_seen_ts) ? 'online' : 'offline'} />
                      </h4>
                      <AreaBadge area={id.area} className="mt-1" />
                    </div>
                  </div>
                  <RiskBadge score={id.risk_score || 0} severidad={scoreToSeverity(id.risk_score || 0)} />
                </div>
                
                <div className="bg-[#0D1117] p-2 rounded border border-[#21262D] mb-3 flex items-center justify-between">
                   <MonoText className="text-[11px]">{id.dispositivo || 'Unknown-Device'}</MonoText>
                   <MonoText className="text-[11px] opacity-70">{id.hostname || 'Unknown-Host'}</MonoText>
                </div>
                
                <div className="flex items-center gap-4 h-10">
                  <div className="flex-1 h-full">
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={history}>
                        <YAxis domain={[0, 100]} hide />
                        <Line type="monotone" dataKey="val" stroke="var(--color-primary)" strokeWidth={2} dot={false} isAnimationActive={false} />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                  
                  {id.delta_2h !== undefined && (
                    <div className="flex flex-col items-center justify-center bg-[#0D1117] px-2 py-1 rounded">
                      <span className="text-[10px] text-[var(--text-sec)]">Δ 2H</span>
                      <span className={`text-xs font-bold ${hasRaised ? 'text-[var(--color-critical)]' : 'text-[var(--color-success)]'}`}>
                        {hasRaised ? '↑' : '↓'} {Math.abs(id.delta_2h)}
                      </span>
                    </div>
                  )}
                </div>
              </Card>
            )
          })}
        </div>
      </div>

      {selectedId && (
        <Card className="w-1/3 min-w-[350px] p-0 flex flex-col h-[calc(100vh-100px)] animate-slide-in-right sticky top-0">
           <div className="p-4 border-b border-[#21262D] flex justify-between items-center bg-[#0D1117]/50">
             <h3 className="font-bold text-white">Identity Dossier</h3>
             <button onClick={() => setSelectedId(null)} className="text-[var(--text-sec)] hover:text-white">✕</button>
           </div>
           
           <div className="p-4 overflow-y-auto flex-1">
             <div className="mb-6">
                <h4 className="text-[11px] uppercase tracking-wider text-[var(--text-sec)] mb-2">Comportamiento Habitual (Baseline)</h4>
                <div className="bg-[#0D1117] p-3 rounded text-sm space-y-2 border border-[#21262D]">
                  <p><strong>Horas Activas:</strong> 09:00 - 18:00 hs</p>
                  <p><strong>Volumen Promedio:</strong> ~125 MB/día</p>
                  <p><strong>Servidores Típicos:</strong> 3 detectados</p>
                </div>
             </div>
             
             <div>
               <h4 className="text-[11px] uppercase tracking-wider text-[var(--text-sec)] mb-2">Desviaciones Críticas</h4>
               <div className="border border-[var(--color-critical)] rounded p-3 bg-[var(--color-critical)]/10 text-sm">
                 <p className="text-[#FF4757]">⚠ Volumen excedió el 500% hace 1 hora.</p>
                 <p className="text-[#FF4757]">⚠ Dominio anómalo contactado 41 veces.</p>
               </div>
             </div>
           </div>
        </Card>
      )}
    </div>
  );
}
