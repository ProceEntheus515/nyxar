import { useState, useEffect } from 'react'
import { identityApi } from '../../api/client'
import styles from './AboutNyxar.module.css'

export function AboutNyxar({ isOpen, onClose }) {
  const [identity, setIdentity] = useState(null)
  const [loading, setLoading] = useState(false)
  const [loadError, setLoadError] = useState(false)

  useEffect(() => {
    if (!isOpen) {
      return undefined
    }
    let cancelled = false
    setLoading(true)
    setLoadError(false)
    identityApi
      .get()
      .then((data) => {
        if (!cancelled) {
          setIdentity(data)
        }
      })
      .catch(() => {
        if (!cancelled) {
          setIdentity(null)
          setLoadError(true)
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false)
        }
      })
    return () => {
      cancelled = true
    }
  }, [isOpen])

  if (!isOpen) {
    return null
  }

  return (
    <div
      className={styles.overlay}
      onClick={onClose}
      onKeyDown={(e) => e.key === 'Escape' && onClose()}
      role="presentation"
    >
      <div
        className={styles.panel}
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="about-nyxar-title"
      >
        <div className={styles.header}>
          <span className={styles.symbol} aria-hidden>
            ⬡
          </span>
          <span className={styles.name} id="about-nyxar-title">
            NYXAR
          </span>
          <button type="button" className={styles.close} onClick={onClose} aria-label="Cerrar">
            ×
          </button>
        </div>

        {loading ? (
          <div className={styles.loading}>Consultando identidad...</div>
        ) : identity ? (
          <>
            <p className={styles.tagline}>{identity.system.tagline_es}</p>

            <div className={styles.section}>
              <span className={styles.sectionLabel}>ORIGEN DEL NOMBRE</span>
              {identity.etymology.components.map((component) => (
                <div key={component.fragment} className={styles.etymologyBlock}>
                  <div className={styles.fragment}>{component.fragment}</div>
                  <div className={styles.fragmentLang}>{component.language}</div>
                  <div className={styles.fragmentMeaning}>{component.meaning}</div>
                  <p className={styles.fragmentDepth}>{component.depth}</p>
                </div>
              ))}
            </div>

            <div className={styles.combined}>
              <p>{identity.etymology.combined_meaning}</p>
            </div>

            <div className={styles.section}>
              <span className={styles.sectionLabel}>CÓMO SE PERCIBE</span>
              {identity.perception.layers.map((layer) => (
                <div key={layer.audience} className={styles.perceptionLayer}>
                  <span className={styles.audience}>{layer.audience}</span>
                  <p className={styles.perceptionText}>{layer.perception}</p>
                </div>
              ))}
            </div>

            <div className={styles.quenyaBlock}>
              <span className={styles.quenyaWord}>{identity.invocation.quenya_reference.word}</span>
              <p className={styles.quenyaConnection}>{identity.invocation.quenya_reference.connection}</p>
            </div>

            <p className={styles.endpointNote}>{identity.meta.endpoint_purpose}</p>

            <div className={styles.footer}>
              <span className={styles.footerText}>GET /api/v1/identity</span>
              <span className={styles.footerVersion}>v{identity.system.version}</span>
            </div>
          </>
        ) : (
          <p className={styles.error}>
            {loadError ? 'No se pudo consultar la identidad.' : 'Sin datos.'}
          </p>
        )}
      </div>
    </div>
  )
}
