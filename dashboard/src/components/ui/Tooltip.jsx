import { useState, useRef, useLayoutEffect, useCallback } from 'react'
import { createPortal } from 'react-dom'
import styles from './Tooltip.module.css'

const SHOW_DELAY_MS = 400
const HIDE_DELAY_MS = 120

const SIDES = new Set(['top', 'bottom', 'left', 'right'])

/**
 * Tooltip con retardo de hover y posición por lado (F07).
 */
export default function Tooltip({ children, content, side = 'top', className = '' }) {
  const s = SIDES.has(side) ? side : 'top'
  const [open, setOpen] = useState(false)
  const [coords, setCoords] = useState({ top: 0, left: 0 })
  const showTimerRef = useRef(null)
  const hideTimerRef = useRef(null)
  const triggerRef = useRef(null)
  const tipRef = useRef(null)

  const clearTimers = useCallback(() => {
    if (showTimerRef.current) window.clearTimeout(showTimerRef.current)
    if (hideTimerRef.current) window.clearTimeout(hideTimerRef.current)
    showTimerRef.current = null
    hideTimerRef.current = null
  }, [])

  const scheduleShow = useCallback(() => {
    clearTimers()
    showTimerRef.current = window.setTimeout(() => setOpen(true), SHOW_DELAY_MS)
  }, [clearTimers])

  const scheduleHide = useCallback(() => {
    clearTimers()
    hideTimerRef.current = window.setTimeout(() => setOpen(false), HIDE_DELAY_MS)
  }, [clearTimers])

  const cancelHide = useCallback(() => {
    if (hideTimerRef.current) window.clearTimeout(hideTimerRef.current)
    hideTimerRef.current = null
  }, [])

  useLayoutEffect(() => {
    if (!open || !triggerRef.current) return

    const place = () => {
      const el = triggerRef.current
      const tip = tipRef.current
      if (!el || !tip) return

      const rect = el.getBoundingClientRect()
      const margin = 8
      const tw = tip.offsetWidth
      const th = tip.offsetHeight
      let top = 0
      let left = 0

      switch (s) {
        case 'bottom':
          top = rect.bottom + margin
          left = rect.left + rect.width / 2 - tw / 2
          break
        case 'left':
          top = rect.top + rect.height / 2 - th / 2
          left = rect.left - tw - margin
          break
        case 'right':
          top = rect.top + rect.height / 2 - th / 2
          left = rect.right + margin
          break
        default:
          top = rect.top - th - margin
          left = rect.left + rect.width / 2 - tw / 2
      }

      const pad = 6
      const maxL = window.innerWidth - tw - pad
      const maxT = window.innerHeight - th - pad
      left = Math.min(maxL, Math.max(pad, left))
      top = Math.min(maxT, Math.max(pad, top))

      setCoords({ top, left })
    }

    place()
    const raf = window.requestAnimationFrame(place)
    return () => window.cancelAnimationFrame(raf)
  }, [open, s])

  useLayoutEffect(() => () => clearTimers(), [clearTimers])

  return (
    <>
      <div
        ref={triggerRef}
        className={`${styles.trigger} ${className}`.trim()}
        onMouseEnter={() => {
          cancelHide()
          scheduleShow()
        }}
        onMouseLeave={scheduleHide}
        onFocus={() => {
          cancelHide()
          scheduleShow()
        }}
        onBlur={scheduleHide}
      >
        {children}
      </div>
      {open &&
        createPortal(
          <div
            ref={tipRef}
            className={`${styles.tooltip} ${styles[`side${s.charAt(0).toUpperCase()}${s.slice(1)}`]}`}
            style={{ top: coords.top, left: coords.left }}
            role="tooltip"
            onMouseEnter={cancelHide}
            onMouseLeave={scheduleHide}
          >
            {content}
          </div>,
          document.body,
        )}
    </>
  )
}
