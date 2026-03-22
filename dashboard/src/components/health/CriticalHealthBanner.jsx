import styles from './CriticalHealthBanner.module.css'

export default function CriticalHealthBanner({ mensaje }) {
  const text =
    mensaje ||
    'Estado crítico detectado en uno o más componentes. Revisá la vista Salud del sistema.'
  return (
    <div className={styles.banner} role="alert">
      {text}
    </div>
  )
}
