import React, { useState } from 'react'
import { useStore } from '../store'
import Card from '../components/ui/Card'
import IdentityRow from '../components/data/IdentityRow'

export default function Identities() {
  const { identities } = useStore()
  const [selectedId, setSelectedId] = useState(null)

  const sortedIdentities = Object.values(identities || {}).sort(
    (a, b) => (b.risk_score || 0) - (a.risk_score || 0),
  )

  return (
    <div className="h-full flex gap-4 w-full min-h-0">
      <div className={`flex-1 flex flex-col min-w-0 transition-all duration-300 ${selectedId ? 'w-2/3' : 'w-full'}`}>
        <h2 className="text-xl font-semibold text-white mb-4 shrink-0">Risk Identities</h2>

        <div className="flex flex-col gap-3 overflow-y-auto pr-1">
          {sortedIdentities.map((id) => (
            <IdentityRow
              key={id.id}
              identity={id}
              onClick={() => setSelectedId(id.id)}
              selected={selectedId === id.id}
            />
          ))}
        </div>
      </div>

      {selectedId && (
        <Card className="w-1/3 min-w-[350px] p-0 flex flex-col h-[calc(100vh-100px)] animate-slide-in-right sticky top-0">
          <div className="p-4 border-b border-[var(--base-border)] flex justify-between items-center bg-[var(--base-deep)]/50">
            <h3 className="font-bold text-white">Identity Dossier</h3>
            <button type="button" onClick={() => setSelectedId(null)} className="text-[var(--text-sec)] hover:text-white">
              ✕
            </button>
          </div>

          <div className="p-4 overflow-y-auto flex-1">
            <div className="mb-6">
              <h4 className="text-[11px] uppercase tracking-wider text-[var(--text-sec)] mb-2">
                Comportamiento habitual (baseline)
              </h4>
              <div className="bg-[var(--base-deep)] p-3 rounded text-sm space-y-2 border border-[var(--base-border)]">
                <p>
                  <strong>Horas activas:</strong> 09:00 - 18:00 hs
                </p>
                <p>
                  <strong>Volumen promedio:</strong> ~125 MB/día
                </p>
                <p>
                  <strong>Servidores típicos:</strong> 3 detectados
                </p>
              </div>
            </div>

            <div>
              <h4 className="text-[11px] uppercase tracking-wider text-[var(--text-sec)] mb-2">
                Desviaciones críticas
              </h4>
              <div className="border border-[var(--color-critical)] rounded p-3 bg-[var(--color-critical)]/10 text-sm">
                <p className="text-[var(--color-critical)]">Volumen excedió el 500% hace 1 hora.</p>
                <p className="text-[var(--color-critical)]">Dominio anómalo contactado 41 veces.</p>
              </div>
            </div>
          </div>
        </Card>
      )}
    </div>
  )
}
