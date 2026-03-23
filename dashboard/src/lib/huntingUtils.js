/**
 * Aplana muestras de detalle_queries para tabla/virtualización (sin pipelines Mongo).
 */
export function flattenHuntResultRows(session, hypothesis) {
  const rows = []
  const qs = hypothesis?.queries_sugeridas || []
  const dq = session?.detalle_queries || []
  dq.forEach((q, i) => {
    const label = qs[i] || `Consulta ${i + 1}`
    const muestra = q.muestra || []
    muestra.forEach((doc, j) => {
      const id = doc?.id || doc?._id || `${i}-${j}`
      rows.push({
        queryIndex: i,
        queryLabel: label,
        doc,
        rowKey: `${i}-${j}-${id}`,
      })
    })
  })
  return rows
}

export function pickEventId(doc) {
  if (!doc || typeof doc !== 'object') return null
  if (typeof doc.id === 'string' && doc.id.startsWith('evt_')) return doc.id
  return doc.id || null
}

/**
 * IPs / usuarios internos únicos presentes en la muestra de una sesión de hunting.
 * Alineado con claves de identidades en Zustand (interno.ip, etc.).
 *
 * @param {{ detalle_queries?: { muestra?: object[] }[] }} session
 * @returns {string[]}
 */
export function extractIdentityIdsFromHuntSession(session) {
  const out = new Set()
  const dq = session?.detalle_queries
  if (!Array.isArray(dq)) return []
  for (const q of dq) {
    for (const doc of q.muestra || []) {
      if (!doc || typeof doc !== 'object') continue
      const interno = doc.interno || {}
      const id =
        interno.ip ||
        interno.ip_asociada ||
        interno.id_usuario ||
        interno.usuario ||
        doc.identidad_id
      if (id != null && String(id).trim()) out.add(String(id).trim())
    }
  }
  return [...out]
}

export function summarizeHuntDoc(doc) {
  if (!doc || typeof doc !== 'object') {
    return { timestamp: '', identidad: '', valor: '', contexto: '' }
  }
  const ts = doc.timestamp || doc.ts || ''
  const interno = doc.interno || {}
  const identidad = interno.ip || interno.id_usuario || interno.usuario || interno.hostname || '—'
  const ext = doc.externo || {}
  const valor = ext.valor || '—'
  const contexto = [doc.source, doc.tipo].filter(Boolean).join(' / ') || '—'
  return { timestamp: String(ts), identidad: String(identidad), valor: String(valor), contexto: String(contexto) }
}
