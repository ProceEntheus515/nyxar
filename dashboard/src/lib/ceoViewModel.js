/**
 * Normaliza respuestas de POST /api/ai/ceo-view y datos mock para la vista ejecutiva.
 * Tres estados de semáforo solamente: verde | naranja | rojo.
 */

/** @typedef {'verde' | 'naranja' | 'rojo'} CeoSemaforo */

/**
 * @param {string} [resumen]
 * @param {string} [accion]
 * @param {string} [titulo]
 * @returns {CeoSemaforo}
 */
export function inferSemaforoFromText(resumen, accion, titulo) {
  const t = `${resumen || ''} ${accion || ''} ${titulo || ''}`.toLowerCase()
  if (/crític|crítica|urgencia|inmediat|grave|ransomware|filtraci[oó]n|breach/i.test(t)) {
    return 'rojo'
  }
  if (/inusual|revisar|atenci[oó]n|elevado|anomal[ií]|desviaci[oó]n/i.test(t)) {
    return 'naranja'
  }
  return 'verde'
}

/**
 * @param {CeoSemaforo} semaforo
 * @param {string} [resumen]
 */
export function deriveCeoHeadlines(semaforo, resumen) {
  const firstSentence = (resumen || '')
    .split(/(?<=[.!?])\s+/)[0]
    ?.trim()
    .replace(/\s+/g, ' ')

  if (semaforo === 'verde') {
    return {
      headline: 'La red opera con normalidad',
      subline: 'No hay incidentes críticos activos.',
    }
  }
  if (semaforo === 'rojo') {
    return {
      headline: 'Hay una situación que requiere atención',
      subline:
        firstSentence && firstSentence.length > 8
          ? truncateText(firstSentence, 140)
          : 'El equipo de seguridad debe coordinar la respuesta sin demora.',
    }
  }
  return {
    headline: 'Hay señales que conviene revisar',
    subline:
      firstSentence && firstSentence.length > 8
        ? truncateText(firstSentence, 160)
        : 'Conviene que dirección reciba un cierre informal en las próximas horas.',
  }
}

function truncateText(s, max) {
  if (s.length <= max) return s
  return `${s.slice(0, max - 1)}…`
}

/**
 * @param {string} [resumen]
 * @returns {string[]}
 */
export function paragraphsFromResumen(resumen) {
  if (!resumen?.trim()) return ['Sin texto de análisis disponible por el momento.']
  const parts = resumen
    .split(/\n\n+/)
    .map((s) => s.trim())
    .filter(Boolean)
  if (parts.length >= 2) return parts.slice(0, 3)
  const sentences = resumen.split(/(?<=[.!?])\s+/).map((s) => s.trim()).filter(Boolean)
  if (sentences.length <= 3) return sentences.length ? sentences : [resumen.trim()]
  const per = Math.max(1, Math.ceil(sentences.length / 3))
  const out = []
  for (let i = 0; i < sentences.length && out.length < 3; i += per) {
    out.push(sentences.slice(i, i + per).join(' '))
  }
  return out
}

/**
 * @param {{ titulo?: string, resumen?: string, acciones?: string }} data
 */
export function normalizeCeoFromApiPayload(data) {
  const titulo = data?.titulo || ''
  const resumen = data?.resumen || ''
  const accion = String(data?.acciones || '').trim()
  const semaforo = inferSemaforoFromText(resumen, accion, titulo)
  const { headline, subline } = deriveCeoHeadlines(semaforo, resumen)
  return {
    id: `MEMO-CEO-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 7)}`,
    tipo: 'ceo',
    created_at: new Date().toISOString(),
    semaforo,
    headline,
    subline,
    paragraphs: paragraphsFromResumen(resumen),
    accion_inmediata: accion || undefined,
  }
}
