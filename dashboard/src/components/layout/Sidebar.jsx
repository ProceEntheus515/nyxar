import { useMemo, useState } from 'react'
import { NavLink } from 'react-router-dom'
import { useStore } from '../../store'
import { NyxarLogo } from './NyxarLogo'
import { AboutNyxar } from './AboutNyxar'
import SidebarNavItem from './SidebarNavItem'
import SidebarHealthDot from './SidebarHealthDot'
import LabSimulatorDock from './LabSimulatorDock'
import AiMemo from '../AiMemo'
import { isDevDataEnabled } from '../../lib/devData'
import styles from './Sidebar.module.css'

function countOpenIncidents(incidents) {
  return (incidents || []).filter((i) => String(i.estado || '').toLowerCase() !== 'cerrado').length
}

function healthDotVariant(wsConnected, healthGeneral) {
  if (!wsConnected) return 'critical'
  const g = String(healthGeneral || '')
    .toLowerCase()
    .normalize('NFD')
    .replace(/\p{M}/gu, '')
  if (g.includes('crit')) return 'critical'
  if (g.includes('warn') || g.includes('degrad') || g.includes('advert')) return 'warning'
  return 'nominal'
}

const PRIMARY_NAV = [
  { id: 'map', path: '/map', icon: '◉', label: 'Red' },
  { id: 'timeline', path: '/timeline', icon: '≡', label: 'Timeline', badgeKey: 'timeline' },
  { id: 'identities', path: '/identities', icon: '◎', label: 'Identidades' },
  { id: 'hunting', path: '/hunting', icon: '◈', label: 'Hunting' },
]

const SECONDARY_NAV = [
  { id: 'responses', path: '/responses', icon: '⚡', label: 'Respuestas', badgeKey: 'responses' },
  { id: 'reports', path: '/reports', icon: '✉', label: 'Reportes' },
  { id: 'ceo', path: '/ceo', icon: '♦', label: 'CEO View' },
]

export function Sidebar({ isNarrowViewport }) {
  const [showAbout, setShowAbout] = useState(false)
  const sidebarCollapsed = useStore((s) => s.sidebarCollapsed)
  const setSidebarCollapsed = useStore((s) => s.setSidebarCollapsed)
  const incidents = useStore((s) => s.incidents)
  const responseProposalsPending = useStore((s) => s.responseProposalsPending)
  const healthGeneral = useStore((s) => s.healthGeneral)
  const healthReport = useStore((s) => s.healthReport)
  const wsConnected = useStore((s) => s.wsConnected)
  const isLabMode = useStore((s) => s.isLabMode)
  const identities = useStore((s) => s.identities)

  const effectiveCollapsed = Boolean(isNarrowViewport || sidebarCollapsed)
  const showCollapseToggle = !isNarrowViewport
  const labSimulatorVisible = isLabMode || isDevDataEnabled

  const timelineBadge = useMemo(() => countOpenIncidents(incidents), [incidents])
  const dotVariant = healthDotVariant(wsConnected, healthGeneral)
  const healthTitle =
    healthReport?.resumen ||
    (wsConnected ? 'Estado del sistema' : 'WebSocket desconectado; reconectando…')

  const badgeFor = (key) => {
    if (key === 'timeline') return timelineBadge
    if (key === 'responses') return responseProposalsPending
    return 0
  }

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

        <nav className={styles.nav} aria-label="Secciones">
          <div className={styles.navBlock}>
            {PRIMARY_NAV.map((item) => (
              <SidebarNavItem
                key={item.id}
                to={item.path}
                icon={item.icon}
                label={item.label}
                collapsed={effectiveCollapsed}
                badgeCount={item.badgeKey ? badgeFor(item.badgeKey) : 0}
              />
            ))}
          </div>

          <hr className={styles.sep} />

          <div className={styles.navBlock}>
            {SECONDARY_NAV.map((item) => (
              <SidebarNavItem
                key={item.id}
                to={item.path}
                icon={item.icon}
                label={item.label}
                collapsed={effectiveCollapsed}
                badgeCount={item.badgeKey ? badgeFor(item.badgeKey) : 0}
              />
            ))}
          </div>
        </nav>

        <AiMemo collapsed={effectiveCollapsed} />

        <div className={styles.footer}>
          <hr className={styles.sep} />

          {labSimulatorVisible ? (
            <LabSimulatorDock collapsed={effectiveCollapsed} identities={identities} />
          ) : null}

          <NavLink
            to="/health"
            className={({ isActive }) =>
              `${styles.systemLink} ${isActive ? styles.systemLinkActive : ''}`.trim()
            }
            title={healthTitle}
            aria-label={effectiveCollapsed ? `Sistema. ${healthTitle}` : undefined}
          >
            <span className={styles.systemIcon} aria-hidden>
              ⊡
            </span>
            {!effectiveCollapsed ? <span className={styles.systemLabel}>Sistema</span> : null}
            <span className={styles.systemDotWrap}>
              <SidebarHealthDot variant={dotVariant} />
            </span>
          </NavLink>

          {showCollapseToggle ? (
            <button
              type="button"
              className={styles.collapseBtn}
              onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
              aria-expanded={!sidebarCollapsed}
              title={sidebarCollapsed ? 'Expandir barra lateral' : 'Colapsar barra lateral'}
            >
              <span className={styles.collapseIcon} aria-hidden>
                ⊟
              </span>
              {!effectiveCollapsed ? <span>Colapsar</span> : null}
            </button>
          ) : null}
        </div>
      </aside>

      <AboutNyxar isOpen={showAbout} onClose={() => setShowAbout(false)} />
    </>
  )
}
