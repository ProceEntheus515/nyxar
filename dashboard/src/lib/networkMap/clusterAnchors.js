/**
 * Posiciones normalizadas (0–1) de anclas de cluster — layout fijo, no force global.
 * Irregular a propósito (no anillo perfecto).
 */
const NORM = {
  IT: { nx: 0.22, ny: 0.16 },
  CONTABILIDAD: { nx: 0.14, ny: 0.42 },
  VENTAS: { nx: 0.76, ny: 0.2 },
  GERENCIA: { nx: 0.82, ny: 0.48 },
  RRHH: { nx: 0.1, ny: 0.64 },
  MARKETING: { nx: 0.48, ny: 0.82 },
  FINANZAS: { nx: 0.36, ny: 0.36 },
  OTROS: { nx: 0.52, ny: 0.52 },
}

/**
 * @param {string} [area]
 * @returns {keyof typeof NORM}
 */
export function areaToClusterKey(area) {
  const s = String(area || '')
    .toLowerCase()
    .normalize('NFD')
    .replace(/\p{M}/gu, '')
  if (s.includes('it') || s.includes('tecno') || s.includes('sistem')) return 'IT'
  if (s.includes('contab')) return 'CONTABILIDAD'
  if (s.includes('venta')) return 'VENTAS'
  if (s.includes('geren')) return 'GERENCIA'
  if (s.includes('rrhh') || s.includes('recurs') || s.includes('humano')) return 'RRHH'
  if (s.includes('market')) return 'MARKETING'
  if (s.includes('finanz')) return 'FINANZAS'
  return 'OTROS'
}

/**
 * @param {keyof typeof NORM} key
 * @param {number} width
 * @param {number} height
 */
export function clusterPixelCenter(key, width, height) {
  const n = NORM[key] || NORM.OTROS
  return { cx: n.nx * width, cy: n.ny * height }
}

/** Etiqueta legible para overlay SVG */
export function clusterLabel(key) {
  if (key === 'IT') return 'IT'
  return key.charAt(0) + key.slice(1).toLowerCase().replace(/_/g, ' ')
}

export function allClusterKeys() {
  return Object.keys(NORM)
}
