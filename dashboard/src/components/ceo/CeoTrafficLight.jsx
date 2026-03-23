import styles from './CeoTrafficLight.module.css'

const GLYPH = {
  verde: '🟢',
  naranja: '🟠',
  rojo: '🔴',
}

const CARD = {
  verde: styles.cardVerde,
  naranja: styles.cardNaranja,
  rojo: styles.cardRojo,
}

export default function CeoTrafficLight({ semaforo, headline, subline }) {
  const key = semaforo === 'naranja' || semaforo === 'rojo' ? semaforo : 'verde'
  return (
    <section className={`${styles.card} ${CARD[key]}`.trim()} aria-labelledby="ceo-traffic-title">
      <div className={styles.glyph} aria-hidden>
        {GLYPH[key]}
      </div>
      <div className={styles.textBlock}>
        <h2 id="ceo-traffic-title" className={styles.headline}>
          {headline}
        </h2>
        <p className={styles.subline}>{subline}</p>
      </div>
    </section>
  )
}
