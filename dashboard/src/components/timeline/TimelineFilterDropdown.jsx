import { useEffect, useRef, useState } from 'react'
import styles from './TimelineFilterDropdown.module.css'

/**
 * Dropdown custom para la barra de filtros del Timeline (sin select nativo).
 */
export default function TimelineFilterDropdown({ label, children }) {
  const [open, setOpen] = useState(false)
  const wrapRef = useRef(null)

  useEffect(() => {
    if (!open) return
    const onDoc = (ev) => {
      if (wrapRef.current && !wrapRef.current.contains(ev.target)) setOpen(false)
    }
    document.addEventListener('mousedown', onDoc)
    return () => document.removeEventListener('mousedown', onDoc)
  }, [open])

  return (
    <div className={styles.wrap} ref={wrapRef}>
      <button
        type="button"
        className={styles.trigger}
        aria-expanded={open}
        onClick={() => setOpen((o) => !o)}
      >
        <span className="min-w-0 truncate">{label}</span>
        <span className={styles.caret} aria-hidden>
          ▾
        </span>
      </button>
      {open ? (
        <div className={styles.menu} role="listbox">
          {children(() => setOpen(false))}
        </div>
      ) : null}
    </div>
  )
}

export function TimelineFilterItem({ active, onPick, children, className = '' }) {
  return (
    <button
      type="button"
      role="option"
      aria-selected={active}
      className={`${styles.item} ${active ? styles.itemActive : ''} ${className}`.trim()}
      onClick={() => onPick()}
    >
      {children}
    </button>
  )
}
