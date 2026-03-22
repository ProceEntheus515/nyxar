/**
 * Lee un custom property del :root (tokens en tokens.css).
 * Útil para D3/Recharts cuando hace falta un color resuelto en JS.
 */
export function readCssVar(name) {
  if (typeof document === 'undefined') return ''
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim()
}
