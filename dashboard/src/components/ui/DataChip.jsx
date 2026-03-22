import { useState, useCallback } from 'react'
import styles from './DataChip.module.css'

const TYPES = new Set(['ip', 'domain', 'hash', 'port', 'user'])

function truncateHash(value) {
  const s = String(value || '')
  if (s.length <= 12) return s
  return `${s.slice(0, 4)}…${s.slice(-4)}`
}

/**
 * Valor técnico inline con color por tipo y copia opcional (F07).
 */
export default function DataChip({
  value,
  type = 'domain',
  copyable = false,
  truncate = false,
  className = '',
}) {
  const t = TYPES.has(type) ? type : 'domain'
  const display =
    t === 'hash' && truncate ? truncateHash(value) : String(value ?? '')

  const [copied, setCopied] = useState(false)

  const onCopy = useCallback(async () => {
    if (!copyable || !value) return
    try {
      await navigator.clipboard.writeText(String(value))
      setCopied(true)
      window.setTimeout(() => setCopied(false), 1500)
    } catch {
      /* ignore */
    }
  }, [copyable, value])

  return (
    <span
      className={`${styles.chip} ${styles[`type${t.charAt(0).toUpperCase()}${t.slice(1)}`]} ${copyable ? styles.copyable : ''} ${className}`.trim()}
    >
      <span className={styles.value} title={truncate && t === 'hash' ? String(value) : undefined}>
        {display}
      </span>
      {copyable ? (
        <button
          type="button"
          className={styles.copyBtn}
          onClick={onCopy}
          aria-label={copied ? 'Copiado' : 'Copiar al portapapeles'}
        >
          {copied ? '✓' : '⧉'}
        </button>
      ) : null}
    </span>
  )
}
