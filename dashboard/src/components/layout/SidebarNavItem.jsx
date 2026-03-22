import { NavLink } from 'react-router-dom'
import styles from './SidebarNavItem.module.css'

/**
 * Item de navegación lateral: NavLink + glifo Unicode + badge opcional.
 * Cumple F06: activo con cyan-dim / cyan-bright y borde cyan-base.
 */
export default function SidebarNavItem({
  to,
  icon,
  label,
  badgeCount = 0,
  collapsed,
  title,
}) {
  const n = typeof badgeCount === 'number' ? badgeCount : 0
  const showBadge = n > 0
  const badgeText = n > 99 ? '99+' : String(n)

  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        [styles.link, collapsed ? styles.linkCollapsed : '', isActive ? styles.linkActive : '']
          .filter(Boolean)
          .join(' ')
      }
      title={title ?? (collapsed ? label : undefined)}
    >
      <span className={styles.icon} aria-hidden>
        {icon}
      </span>
      {!collapsed ? <span className={styles.label}>{label}</span> : null}
      {showBadge ? (
        <span className={styles.badge} aria-label={`${badgeText} pendientes`}>
          {badgeText}
        </span>
      ) : null}
    </NavLink>
  )
}
