import { useState, useEffect } from 'react'
import { NyxarLogo } from './NyxarLogo'
import { AboutNyxar } from './AboutNyxar'
import styles from './Sidebar.module.css'

const NAV = [
  { id: 'map', label: 'Network Graph', short: 'N' },
  { id: 'timeline', label: 'Live Events Timeline', short: 'T' },
  { id: 'identities', label: 'Risk Identities', short: 'I' },
  { id: 'hunting', label: 'Threat Hunting', short: 'H' },
  { id: 'health', label: 'Salud del sistema', short: 'S' },
]

export function Sidebar({ activeTab, onTabChange, healthCritical }) {
  const [showAbout, setShowAbout] = useState(false)
  const [collapsed, setCollapsed] = useState(false)

  useEffect(() => {
    const mq = window.matchMedia('(max-width: 767px)')
    const apply = () => setCollapsed(mq.matches)
    apply()
    mq.addEventListener('change', apply)
    return () => mq.removeEventListener('change', apply)
  }, [])

  return (
    <>
      <aside
        className={`${styles.sidebar} ${collapsed ? styles.sidebarCollapsed : ''}`}
        aria-label="Navegación principal"
      >
        <button
          type="button"
          className={styles.logoButton}
          onClick={() => setShowAbout(true)}
          title="¿Qué es NYXAR?"
          aria-label="Ver identidad del sistema"
        >
          <NyxarLogo collapsed={collapsed} />
        </button>

        <nav className={styles.nav}>
          {NAV.map((item) => (
            <button
              key={item.id}
              type="button"
              className={`${styles.navButton} ${activeTab === item.id ? styles.navButtonActive : ''} ${
                item.id === 'health' && healthCritical ? styles.navButtonCriticalPulse : ''
              }`}
              onClick={() => onTabChange(item.id)}
              title={item.label}
              aria-current={activeTab === item.id ? 'page' : undefined}
            >
              {collapsed ? item.short : item.label}
            </button>
          ))}
        </nav>

        <div className={styles.collapseToggle}>
          <button
            type="button"
            className={styles.collapseBtn}
            onClick={() => setCollapsed((c) => !c)}
            aria-expanded={!collapsed}
          >
            {collapsed ? '»' : '«'}
          </button>
        </div>
      </aside>

      <AboutNyxar isOpen={showAbout} onClose={() => setShowAbout(false)} />
    </>
  )
}
