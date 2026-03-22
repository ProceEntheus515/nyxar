export const RISK_COLORS = {
  critica: { bg: 'var(--color-critical)', text: '#FFFFFF', label: 'CRÍTICA' },
  alta:    { bg: 'var(--color-warning)', text: '#000000', label: 'ALTA' },
  media:   { bg: 'var(--color-media)', text: '#000000', label: 'MEDIA' },
  baja:    { bg: 'var(--color-baja)', text: '#000000', label: 'BAJA' },
  info:    { bg: 'var(--color-info)', text: '#FFFFFF', label: 'INFO' },
}

export const scoreToSeverity = (score) => {
  if (score >= 80) return 'critica'
  if (score >= 60) return 'alta'
  if (score >= 40) return 'media'
  if (score >= 20) return 'baja'
  return 'info'
}
