/**
 * Helpers de color semántico (NYXAR).
 * Diferencia importante: scoreToColor mapea risk score 0–100 a buckets de UI;
 * scoreToSeverity + RISK_COLORS en utils.js son para severidad de incidente (API).
 */

const AREA_PALETTE_VARS = [
  'var(--area-palette-0)',
  'var(--area-palette-1)',
  'var(--area-palette-2)',
  'var(--area-palette-3)',
  'var(--area-palette-4)',
  'var(--area-palette-5)',
  'var(--area-palette-6)',
  'var(--area-palette-7)',
]

function clampScore(score) {
  const n = Number(score)
  if (!Number.isFinite(n)) return 0
  return Math.min(100, Math.max(0, n))
}

/**
 * Convierte un risk score (0–100) a tokens de color y etiqueta de bucket.
 *
 * @param {number} score
 * @returns {{ color: string, bg: string, border: string, label: string }}
 */
export function scoreToColor(score) {
  const s = clampScore(score)
  if (s < 20) {
    return {
      color: 'var(--clean-bright)',
      bg: 'var(--clean-bg)',
      border: 'var(--clean-border)',
      label: 'NOMINAL',
    }
  }
  if (s < 40) {
    return {
      color: 'var(--info-bright)',
      bg: 'var(--info-bg)',
      border: 'var(--info-border)',
      label: 'BAJO',
    }
  }
  if (s < 60) {
    return {
      color: 'var(--medium-bright)',
      bg: 'var(--medium-bg)',
      border: 'var(--medium-border)',
      label: 'MEDIO',
    }
  }
  if (s < 80) {
    return {
      color: 'var(--high-bright)',
      bg: 'var(--high-bg)',
      border: 'var(--high-border)',
      label: 'ALTO',
    }
  }
  return {
    color: 'var(--critical-bright)',
    bg: 'var(--critical-bg)',
    border: 'var(--critical-border)',
    label: 'CRÍTICO',
  }
}

/**
 * Color e icono por fuente de datos; consistente en toda la app.
 */
export const SOURCE_COLORS = {
  dns: { color: 'var(--cyan-base)', icon: '◈', label: 'DNS' },
  proxy: { color: 'var(--info-bright)', icon: '◎', label: 'PROXY' },
  firewall: { color: 'var(--high-bright)', icon: '◉', label: 'FW' },
  wazuh: { color: 'var(--medium-bright)', icon: '◆', label: 'WAZUH' },
  endpoint: { color: 'var(--base-soft)', icon: '◇', label: 'HOST' },
  misp: { color: 'var(--critical-bright)', icon: '⬡', label: 'MISP' },
}

/**
 * @param {string} [source]
 * @returns {keyof typeof SOURCE_COLORS | null}
 */
export function normalizeSourceKey(source) {
  const s = (source || '').toLowerCase()
  if (s.includes('misp')) return 'misp'
  if (s.includes('dns')) return 'dns'
  if (s.includes('proxy') || s.includes('squid')) return 'proxy'
  if (s.includes('firewall')) return 'firewall'
  if (s.includes('wazuh')) return 'wazuh'
  if (s.includes('endpoint')) return 'endpoint'
  return null
}

/**
 * Color estable por nombre de área (hash determinista; paleta azul-teal en tokens).
 *
 * @param {string} [area]
 * @returns {string} referencia CSS var(--area-palette-N)
 */
export function areaToColor(area) {
  const str = area || ''
  let hash = 0
  for (let i = 0; i < str.length; i++) {
    hash = str.charCodeAt(i) + ((hash << 5) - hash)
  }
  return AREA_PALETTE_VARS[Math.abs(hash) % AREA_PALETTE_VARS.length]
}

/** Opacidades permitidas para estados UI; evitar valores arbitrarios. */
export const OPACITY = {
  disabled: 0.35,
  muted: 0.55,
  soft: 0.7,
  full: 1.0,
}
