import { readCssVar } from '../../styles/cssVar'

/**
 * Resuelve `var(--token)` a valor computado para SVG/Recharts cuando hace falta color literal.
 */
export function resolveToken(colorRef) {
  if (!colorRef || typeof colorRef !== 'string') return ''
  const m = colorRef.trim().match(/^var\(\s*(--[^)]+)\s*\)$/i)
  if (m) {
    const v = readCssVar(m[1])
    return v || colorRef
  }
  return colorRef.trim()
}
