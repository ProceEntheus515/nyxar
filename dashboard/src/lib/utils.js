export const RISK_COLORS = {
  critica: { bg: 'var(--color-critical)', text: 'var(--base-bright)', label: 'CRÍTICA' },
  alta: { bg: 'var(--color-warning)', text: 'var(--base-deep)', label: 'ALTA' },
  media: { bg: 'var(--color-media)', text: 'var(--base-deep)', label: 'MEDIA' },
  baja: { bg: 'var(--color-baja)', text: 'var(--base-deep)', label: 'BAJA' },
  info: { bg: 'var(--color-info)', text: 'var(--base-bright)', label: 'INFO' },
}

export const scoreToSeverity = (score) => {
  if (score >= 80) return 'critica'
  if (score >= 60) return 'alta'
  if (score >= 40) return 'media'
  if (score >= 20) return 'baja'
  return 'info'
}
