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
