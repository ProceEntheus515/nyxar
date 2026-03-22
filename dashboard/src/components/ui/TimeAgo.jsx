import { useState, useEffect } from 'react'
import styles from './TimeAgo.module.css'

function formatRelative(iso) {
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return 'fecha inválida'

  const now = Date.now()
  const diffSec = Math.floor((now - date.getTime()) / 1000)

  if (diffSec < 0) {
    return date.toLocaleString('es', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  if (diffSec < 60) return 'hace un momento'

  const diffMin = Math.floor(diffSec / 60)
  if (diffMin < 60) return diffMin === 1 ? 'hace 1 min' : `hace ${diffMin} min`

  const diffH = Math.floor(diffMin / 60)
  if (diffH < 24) return diffH === 1 ? 'hace 1 h' : `hace ${diffH} h`

  const diffD = Math.floor(diffH / 24)
  if (diffD <= 7) return diffD === 1 ? 'hace 1 d' : `hace ${diffD} d`

  return date.toLocaleString('es', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

/**
 * Tiempo relativo en español, actualizado cada 30 s (F07).
 */
export default function TimeAgo({ timestamp, className = '' }) {
  const [text, setText] = useState(() => formatRelative(timestamp))

  useEffect(() => {
    setText(formatRelative(timestamp))
    const id = window.setInterval(() => {
      setText(formatRelative(timestamp))
    }, 30000)
    return () => window.clearInterval(id)
  }, [timestamp])

  return (
    <time
      className={`${styles.time} ${className}`.trim()}
      dateTime={timestamp}
      title={new Date(timestamp).toLocaleString('es')}
    >
      {text}
    </time>
  )
}
