/**
 * Texto relativo breve en español para sellos de tiempo en UI.
 */
export function formatRelativeTimeEs(iso) {
  const t = new Date(iso).getTime()
  if (!Number.isFinite(t)) return 'fecha desconocida'
  const sec = Math.max(0, Math.round((Date.now() - t) / 1000))
  if (sec < 45) return 'hace un momento'
  const min = Math.floor(sec / 60)
  if (min < 60) return min <= 1 ? 'hace 1 minuto' : `hace ${min} minutos`
  const h = Math.floor(min / 60)
  if (h < 24) return h === 1 ? 'hace 1 hora' : `hace ${h} horas`
  const d = Math.floor(h / 24)
  if (d < 7) return d === 1 ? 'hace 1 día' : `hace ${d} días`
  const w = Math.floor(d / 7)
  return w === 1 ? 'hace 1 semana' : `hace ${w} semanas`
}
