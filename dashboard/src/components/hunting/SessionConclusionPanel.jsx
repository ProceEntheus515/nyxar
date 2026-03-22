import styles from './SessionConclusionPanel.module.css'

export function SessionConclusionPanel({ conclusion, onGoTimeline }) {
  if (!conclusion) {
    return (
      <section className={styles.section} aria-labelledby="hunt-concl-title">
        <h2 id="hunt-concl-title" className={styles.heading}>
          Conclusión de Claude
        </h2>
        <p className={styles.muted}>Aún no hay conclusión para esta sesión.</p>
      </section>
    )
  }

  const c = conclusion
  const conf = c.confianza || 'baja'

  return (
    <section className={styles.section} aria-labelledby="hunt-concl-title">
      <h2 id="hunt-concl-title" className={styles.heading}>
        Conclusión de Claude
      </h2>
      <div className={styles.card}>
        <div className={styles.row}>
          <span className={styles.tag} data-found={c.encontrado ? 'yes' : 'no'}>
            {c.encontrado ? 'Hallazgos positivos' : 'Sin evidencia clara'}
          </span>
          <span className={styles.conf} data-conf={conf}>
            Confianza: {conf}
          </span>
        </div>
        <p className={styles.summary}>{c.resumen}</p>
        {Array.isArray(c.evidencia) && c.evidencia.length > 0 && (
          <div className={styles.evBlock}>
            <h3 className={styles.sub}>Evidencia clave</h3>
            <ul className={styles.evList}>
              {c.evidencia.map((ev, i) => (
                <li key={i}>{typeof ev === 'object' ? ev.descripcion || JSON.stringify(ev) : String(ev)}</li>
              ))}
            </ul>
          </div>
        )}
        {Array.isArray(c.iocs_nuevos) && c.iocs_nuevos.length > 0 && (
          <div className={styles.evBlock}>
            <h3 className={styles.sub}>IOCs nuevos</h3>
            <ul className={styles.iocList}>
              {c.iocs_nuevos.map((ioc) => (
                <li key={ioc}>
                  <code className={styles.code}>{ioc}</code>
                </li>
              ))}
            </ul>
          </div>
        )}
        {c.crear_incidente && (
          <div className={styles.incidentBox}>
            <p className={styles.incidentText}>
              El motor marcó esta sesión para generar incidente formal. Si la API lo aplicó, el registro aparece en
              incidentes y alertas.
            </p>
            <button type="button" className={styles.btnOutline} onClick={() => onGoTimeline?.()}>
              Abrir Timeline
            </button>
          </div>
        )}
      </div>
    </section>
  )
}
