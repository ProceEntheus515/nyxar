import React, { useState } from 'react';
import Card from '../components/ui/Card';

// Professional SVG Icons
const TargetIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="10"></circle>
    <circle cx="12" cy="12" r="6"></circle>
    <circle cx="12" cy="12" r="2"></circle>
  </svg>
);

const PlayIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polygon points="5 3 19 12 5 21 5 3"></polygon>
  </svg>
);

export default function AttackInjector({ isLabMode, identities = {} }) {
  const [isOpen, setIsOpen] = useState(false);
  const [scenario, setScenario] = useState('phishing');
  const [target, setTarget] = useState('');
  const [intensity, setIntensity] = useState('media');
  const [loading, setLoading] = useState(false);
  const [logs, setLogs] = useState([]);

  if (!isLabMode) return null;

  const handleInject = async () => {
    if (!target) return;
    setLoading(true);
    try {
      const res = await fetch('http://localhost:8000/api/v1/simulator/scenario', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ scenario, target, intensity })
      });
      const data = await res.json();
      if (res.ok) {
        setLogs(prev => [{ id: data.data.scenario_id, text: `Ataque ${scenario} iniciado vs ${target}` }, ...prev].slice(0, 3));
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
      setIsOpen(false);
    }
  };

  return (
    <div className="fixed bottom-6 right-6 z-50 flex flex-col items-end">
      {isOpen && (
        <Card className="w-80 mb-4 p-4 shadow-2xl glass-panel">
          <h3 className="text-white font-semibold mb-4 flex items-center gap-2">
            <TargetIcon /> Command & Control (Simulator)
          </h3>
          
          <div className="flex flex-col gap-3">
            <div>
              <label className="text-[11px] text-[var(--text-sec)] uppercase tracking-wider">Escenario</label>
              <select 
                className="w-full mt-1 bg-[#0D1117] border border-[#21262D] rounded p-2 text-sm text-white outline-none focus:border-[var(--color-critical)]"
                value={scenario}
                onChange={e => setScenario(e.target.value)}
              >
                <option value="phishing">Phishing Campaign</option>
                <option value="ransomware">Ransomware Detonation</option>
                <option value="dns_tunneling">DNS Tunneling</option>
                <option value="lateral_movement">Lateral Movement (WMI/SMB)</option>
                <option value="exfiltration">Data Exfiltration</option>
              </select>
            </div>

            <div>
              <label className="text-[11px] text-[var(--text-sec)] uppercase tracking-wider">Target Identidad</label>
              <select 
                className="w-full mt-1 bg-[#0D1117] border border-[#21262D] rounded p-2 text-sm text-white outline-none focus:border-[var(--color-critical)]"
                value={target}
                onChange={e => setTarget(e.target.value)}
              >
                <option value="">-- Seleccionar Target --</option>
                {Object.values(identities).map(id => (
                  <option key={id.id} value={id.id}>{id.nombre_completo} ({id.area})</option>
                ))}
              </select>
            </div>

            <div>
              <label className="text-[11px] text-[var(--text-sec)] uppercase tracking-wider">Intensidad</label>
              <div className="flex gap-2 mt-1">
                {['baja', 'media', 'alta'].map(lvl => (
                  <button
                    key={lvl}
                    onClick={() => setIntensity(lvl)}
                    className={`flex-1 py-1 text-xs rounded border ${intensity === lvl ? 'bg-[var(--color-critical)] border-[var(--color-critical)] text-white' : 'border-[#21262D] text-[var(--text-sec)]'}`}
                  >
                    {lvl.toUpperCase()}
                  </button>
                ))}
              </div>
            </div>

            <button
              onClick={handleInject}
              disabled={loading || !target}
              className="mt-2 w-full flex items-center justify-center gap-2 bg-[var(--color-critical)] hover:bg-[#ff5c6b] text-white py-2 rounded font-semibold text-sm transition-colors disabled:opacity-50"
            >
              {loading ? 'Preparando payload...' : <><PlayIcon /> Ejecutar Ataque</>}
            </button>
          </div>

          {logs.length > 0 && (
            <div className="mt-4 pt-4 border-t border-[#21262D]">
              <h4 className="text-[11px] text-[var(--text-sec)] uppercase mb-2">Últimos inyectados</h4>
              {logs.map(log => (
                <div key={log.id} className="text-xs text-[var(--color-warning)] mb-1 font-mono">
                  &gt; {log.text}
                </div>
              ))}
            </div>
          )}
        </Card>
      )}

      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-14 h-14 bg-[#161B22] border-2 border-[var(--color-critical)] rounded-full flex items-center justify-center text-[var(--color-critical)] hover:bg-[var(--color-critical)] hover:text-white transition-all shadow-lg shadow-red-500/20"
        aria-label="Abrir Inyector de Ataques LAB"
      >
        <TargetIcon />
      </button>
    </div>
  );
}
