import { useState } from 'react'
import { NavLink } from 'react-router-dom'
import { useStore } from '../../store'
import { NyxarLogo } from './NyxarLogo'
import { AboutNyxar } from './AboutNyxar'
import styles from './Sidebar.module.css'

const NAV = [
  { id: 'map', path: '/map', label: 'Network Graph', short: 'N' },
  { id: 'timeline', path: '/timeline', label: 'Live Events Timeline', short: 'T' },
  { id: 'identities', path: '/identities', label: 'Risk Identities', short: 'I' },
  { id: 'hunting', path: '/hunting', label: 'Threat Hunting', short: 'H' },
  { id: 'health', path: '/health', label: 'Salud del sistema', short: 'S' },
]

export function Sidebar({ healthCritical, isNarrowViewport }) {
  const [showAbout, setShowAbout] = useState(false)
  const sidebarCollapsed = useStore((s) => s.sidebarCollapsed)
  const setSidebarCollapsed = useStore((s) => s.setSidebarCollapsed)

  const effectiveCollapsed = Boolean(isNarrowViewport || sidebarCollapsed)
  const showCollapseToggle = !isNarrowViewport

  return (
    <>
      <aside
        className={`${styles.sidebar} ${effectiveCollapsed ? styles.sidebarCollapsed : ''}`}
        aria-label="Navegación principal"
      >
        <button
          type="button"
          className={styles.logoButton}
          onClick={() => setShowAbout(true)}
          title="¿Qué es NYXAR?"
          aria-label="Ver identidad del sistema"
        >
          <NyxarLogo collapsed={effectiveCollapsed} />
        </button>

        <nav className={styles.nav}>
          {NAV.map((item) => (
            <NavLink
              key={item.id}
              to={item.path}
              className={({ isActive }) =>
                `${styles.navButton} ${isActive ? styles.navButtonActive : ''} ${
                  item.id === 'health' && healthCritical ? styles.navButtonCriticalPulse : ''
                }`
              }
              title={item.label}
            >
              {effectiveCollapsed ? item.short : item.label}
            </NavLink>
          ))}
        </nav>

        {showCollapseToggle ? (
          <div className={styles.collapseToggle}>
            <button
              type="button"
              className={styles.collapseBtn}
              onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
              aria-expanded={!sidebarCollapsed}
            >
              {sidebarCollapsed ? '»' : '«'}
            </button>
          </div>
        ) : null}
      </aside>

      <AboutNyxar isOpen={showAbout} onClose={() => setShowAbout(false)} />
    </>
  )
}
