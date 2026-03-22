import { useEffect } from 'react'
import { Outlet, useLocation } from 'react-router-dom'
import { useStore } from '../../store'
import { useMediaQuery } from '../../hooks/useMediaQuery'
import CriticalHealthBanner from '../health/CriticalHealthBanner'
import { Sidebar } from './Sidebar'
import DetailPanel from './DetailPanel'
import styles from './AppShell.module.css'

const TAB_TITLES = {
  map: 'NYXAR — Red',
  timeline: 'NYXAR — Timeline',
  identities: 'NYXAR — Identidades',
  hunting: 'NYXAR — Hunting',
  responses: 'NYXAR — Respuestas',
  reports: 'NYXAR — Reportes',
  ceo: 'NYXAR — CEO View',
  health: 'NYXAR — Sistema',
}

function normalizeSev(s) {
  return String(s || '')
    .toLowerCase()
    .normalize('NFD')
    .replace(/\p{M}/gu, '')
}

function hasActiveCriticalAlert(incidents, alerts) {
  const lists = [incidents || [], alerts || []]
  for (const list of lists) {
    for (const item of list) {
      const sev = normalizeSev(item.severidad)
      if (sev.includes('crit')) return true
    }
  }
  return false
}

export default function AppShell() {
  const location = useLocation()
  const isWide = useMediaQuery('(min-width: 1280px)')
  const isNarrowViewport = useMediaQuery('(max-width: 767px)')

  const healthGeneral = useStore((s) => s.healthGeneral)
  const healthReport = useStore((s) => s.healthReport)
  const incidents = useStore((s) => s.incidents)
  const alerts = useStore((s) => s.alerts)
  const sidebarCollapsed = useStore((s) => s.sidebarCollapsed)
  const detailOpen = useStore((s) => s.detailPanel.isOpen)

  const sidebarPx = isNarrowViewport ? 56 : sidebarCollapsed ? 56 : 220
  const detailCol =
    isWide && detailOpen ? 'minmax(0, var(--panel-width))' : 'minmax(0, 0px)'

  const showCriticalStripe = hasActiveCriticalAlert(incidents, alerts)
  const showHealthBanner = healthGeneral === 'critico'

  useEffect(() => {
    const seg = location.pathname.replace(/^\//, '') || 'map'
    document.title = TAB_TITLES[seg] || 'NYXAR'
  }, [location.pathname])

  return (
    <>
      <div
        className={`${styles.root} ${showCriticalStripe ? styles.shellCritical : ''}`}
        style={{
          '--sidebar-width': `${sidebarPx}px`,
          '--detail-col': detailCol,
        }}
      >
        {showHealthBanner ? (
          <CriticalHealthBanner mensaje={healthReport?.resumen} className={styles.banner} />
        ) : null}

        <div className={styles.gridBody}>
          <div className={styles.nav}>
            <Sidebar isNarrowViewport={isNarrowViewport} />
          </div>

          <main className={styles.main}>
            <div key={location.pathname} className={`${styles.outletFade} ${styles.outletScroll}`}>
              <Outlet />
            </div>
          </main>

          {isWide && detailOpen ? (
            <div className={styles.detailSlot}>
              <DetailPanel wideLayout />
            </div>
          ) : null}
        </div>
      </div>

      {!isWide && detailOpen ? <DetailPanel wideLayout={false} /> : null}
    </>
  )
}
