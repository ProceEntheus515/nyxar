/**
 * Cliente HTTP mínimo para la API NYXAR (mismo origen en prod o proxy Vite en dev).
 */

const jsonOrThrow = async (response) => {
  const body = await response.json().catch(() => ({}))
  if (!response.ok) {
    const msg = body?.error || body?.message || `HTTP ${response.status}`
    throw new Error(msg)
  }
  return body
}

export const huntingApi = {
  listHypotheses: async (params = {}) => {
    const q = new URLSearchParams()
    if (params.limit != null) q.set('limit', String(params.limit))
    if (params.offset != null) q.set('offset', String(params.offset))
    const url = `/api/v1/hunting/hypotheses${q.toString() ? `?${q}` : ''}`
    const response = await fetch(url)
    return jsonOrThrow(response)
  },

  createHypothesis: async ({ descripcion, hunter }) => {
    const response = await fetch('/api/v1/hunting/hypotheses', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ descripcion, hunter: hunter || 'analista_manual' }),
    })
    return jsonOrThrow(response)
  },

  runHunt: async (hypothesisId, iniciadoBy = 'dashboard_analista') => {
    const q = new URLSearchParams({ iniciado_by: iniciadoBy })
    const response = await fetch(
      `/api/v1/hunting/hypotheses/${encodeURIComponent(hypothesisId)}/run?${q}`,
      { method: 'POST' }
    )
    return jsonOrThrow(response)
  },

  listSessions: async (params = {}) => {
    const q = new URLSearchParams()
    if (params.estado) q.set('estado', params.estado)
    if (params.limit != null) q.set('limit', String(params.limit))
    const url = `/api/v1/hunting/sessions${q.toString() ? `?${q}` : ''}`
    const response = await fetch(url)
    return jsonOrThrow(response)
  },

  getSession: async (sessionId) => {
    const response = await fetch(`/api/v1/hunting/sessions/${encodeURIComponent(sessionId)}`)
    return jsonOrThrow(response)
  },
}

export const identityApi = {
  /**
   * Identidad completa del sistema (GET /api/v1/identity).
   * El servidor envía Cache-Control 24h; aquí no duplicamos caché en memoria.
   */
  get: async () => {
    const response = await fetch('/api/v1/identity')
    if (!response.ok) {
      throw new Error(`identity ${response.status}`)
    }
    return response.json()
  },
}
