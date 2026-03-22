import styles from './Badge.module.css'

const VARIANTS = new Set(['default', 'critical', 'high', 'medium', 'clean', 'info', 'cyan'])
const SIZES = new Set(['sm', 'md'])

/**
 * Píldora semántica con borde sutil (NYXAR F07).
 */
export default function Badge({
  variant = 'default',
  size = 'md',
  children,
  dot = false,
  className = '',
}) {
  const v = VARIANTS.has(variant) ? variant : 'default'
  const s = SIZES.has(size) ? size : 'md'

  return (
    <span
      className={`${styles.badge} ${styles[`size${s.charAt(0).toUpperCase()}${s.slice(1)}`]} ${styles[`variant${v.charAt(0).toUpperCase()}${v.slice(1)}`]} ${className}`.trim()}
    >
      {dot ? (
        <span className={styles.dot} aria-hidden>
          <span className={styles.dotInner} />
        </span>
      ) : null}
      {children}
    </span>
  )
}
