import styles from './Skeleton.module.css'

/**
 * Placeholder de carga con shimmer horizontal (F07). Usar solo si la carga supera ~200 ms.
 */
export default function Skeleton({
  width = '100%',
  height = '20px',
  rounded = true,
  circle = false,
  className = '',
}) {
  const shapeClass = circle ? styles.circle : rounded ? styles.rounded : styles.square

  return (
    <div
      className={`${styles.root} ${shapeClass} ${className}`.trim()}
      style={{ width, height }}
      role="status"
      aria-label="Cargando"
      aria-busy="true"
    />
  )
}
