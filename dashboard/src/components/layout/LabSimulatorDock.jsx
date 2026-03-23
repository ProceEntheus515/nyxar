import { useState } from 'react'
import styles from './LabSimulatorDock.module.css'

function TargetGlyph() {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden
    >
      <circle cx="12" cy="12" r="10" />
      <circle cx="12" cy="12" r="6" />
      <circle cx="12" cy="12" r="2" />
    </svg>
  )
}

function PlayGlyph() {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden
    >
      <polygon points="5 3 19 12 5 21 5 3" />
    </svg>
  )
}

/**
 * Simulador de ataques (LAB): integrado al sidebar, sin FAB flotante.
 */
export default function LabSimulatorDock({ collapsed, identities = {} }) {
  const [isOpen, setIsOpen] = useState(false)
  const [scenario, setScenario] = useState('phishing')
  const [target, setTarget] = useState('')
  const [intensity, setIntensity] = useState('media')
  const [loading, setLoading] = useState(false)
  const [logs, setLogs] = useState([])

  const handleInject = async () => {
    if (!target) return
    setLoading(true)
    try {
      const res = await fetch('http://localhost:8000/api/v1/simulator/scenario', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ scenario, target, intensity }),
      })
      const data = await res.json()
      if (res.ok) {
        setLogs((prev) =>
          [{ id: data.data.scenario_id, text: `Ataque ${scenario} iniciado vs ${target}` }, ...prev].slice(0, 3),
        )
      }
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
      setIsOpen(false)
    }
  }

  return (
    <div className={`${styles.wrap} ${collapsed ? styles.wrapCollapsed : ''}`.trim()}>
      {isOpen ? (
        <div className={styles.panel}>
          <h3 className={styles.panelTitle}>
            <TargetGlyph />
            Escenarios (LAB)
          </h3>

          <div className={styles.field}>
            <label className={styles.label} htmlFor="lab-scenario">
              Escenario
            </label>
            <select
              id="lab-scenario"
              className={styles.select}
              value={scenario}
              onChange={(e) => setScenario(e.target.value)}
            >
              <option value="phishing">Phishing</option>
              <option value="ransomware">Ransomware</option>
              <option value="dns_tunneling">DNS tunneling</option>
              <option value="lateral_movement">Movimiento lateral</option>
              <option value="exfiltration">Exfiltración</option>
            </select>
          </div>

          <div className={styles.field}>
            <label className={styles.label} htmlFor="lab-target">
              Identidad objetivo
            </label>
            <select
              id="lab-target"
              className={styles.select}
              value={target}
              onChange={(e) => setTarget(e.target.value)}
            >
              <option value="">Seleccionar…</option>
              {Object.values(identities).map((id) => (
                <option key={id.id} value={id.id}>
                  {id.nombre_completo} ({id.area})
                </option>
              ))}
            </select>
          </div>

          <div className={styles.field}>
            <span className={styles.label}>Intensidad</span>
            <div className={styles.intensityRow}>
              {['baja', 'media', 'alta'].map((lvl) => (
                <button
                  key={lvl}
                  type="button"
                  className={`${styles.intensityBtn} ${intensity === lvl ? styles.intensityBtnActive : ''}`.trim()}
                  onClick={() => setIntensity(lvl)}
                >
                  {lvl}
                </button>
              ))}
            </div>
          </div>

          <button
            type="button"
            className={styles.runBtn}
            onClick={handleInject}
            disabled={loading || !target}
          >
            {loading ? 'Enviando…' : (
              <>
                <PlayGlyph />
                Ejecutar
              </>
            )}
          </button>

          {logs.length > 0 ? (
            <div className={styles.logs}>
              <h4 className={styles.logsTitle}>Últimos</h4>
              {logs.map((log) => (
                <div key={log.id} className={styles.logLine}>
                  &gt; {log.text}
                </div>
              ))}
            </div>
          ) : null}
        </div>
      ) : null}

      <button
        type="button"
        className={`${styles.trigger} ${isOpen ? styles.triggerOpen : ''}`.trim()}
        onClick={() => setIsOpen((o) => !o)}
        aria-expanded={isOpen}
        title={collapsed ? 'Simulador LAB' : undefined}
        aria-label="Simulador de escenarios LAB"
      >
        <span className={styles.triggerIcon}>
          <TargetGlyph />
        </span>
        {!collapsed ? <span className={styles.triggerLabel}>Simulador LAB</span> : null}
      </button>
    </div>
  )
}
