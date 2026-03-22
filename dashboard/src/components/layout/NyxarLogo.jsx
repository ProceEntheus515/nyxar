import { useState, useCallback } from 'react'
import styles from './NyxarLogo.module.css'

/** Marca sin texto (sidebar + texto NYXAR en React). */
export const NYXAR_LOGO_SVG = '/branding/nyxar-logo.svg'
/** Variante con [ NYXAR ] incrustado; usar donde no haya texto duplicado. */
export const NYXAR_LOGO_FULL_SVG = '/branding/nyxar-logo-full.svg'
export const NYXAR_LOGO_PNG = '/branding/nyxar-logo.png'

export function NyxarLogo({ collapsed }) {
  const [src, setSrc] = useState(collapsed ? NYXAR_LOGO_SVG : NYXAR_LOGO_FULL_SVG)
  const [useGlyph, setUseGlyph] = useState(false)

  const handleImgError = useCallback(() => {
    if (src === NYXAR_LOGO_FULL_SVG) {
      setSrc(NYXAR_LOGO_SVG)
      return
    }
    if (src === NYXAR_LOGO_SVG) {
      setSrc(NYXAR_LOGO_PNG)
      return
    }
    setUseGlyph(true)
  }, [src])

  return (
    <div className={styles.logo}>
      {useGlyph ? (
        <span className={styles.logoSymbol} aria-hidden>
          ⬡
        </span>
      ) : (
        <img
          src={src}
          alt="NYXAR"
          className={collapsed ? styles.logoImageCollapsed : styles.logoImage}
          onError={handleImgError}
          decoding="async"
        />
      )}
    </div>
  )
}
