/**
 * Cliente HTTP central del dashboard (I06). Las vistas no usan fetch() directo.
 * Base: VITE_API_URL (incluye /api/v1), p. ej. http://localhost:8000/api/v1
 */

const API_BASE = (import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1').replace(
  /\/$/,
  '',
)

/** Origen del servidor sin sufijo /api/v1 (para rutas como /health/detail). */
function getServerOrigin() {
  const stripped = API_BASE.replace(/\/api\/v1$/i, '')
  return stripped || 'http://localhost:8000'
}

export class ApiError extends Error {
  constructor(status, message, endpoint) {
    super(message)
    this.status = status
    this.endpoint = endpoint
    this.name = 'ApiError'
  }
}

/**
 * Petición bajo API_BASE (/api/v1/...).
 */
async function request(endpoint, options = {}) {
  const path = endpoint.startsWith('/') ? endpoint : `/${endpoint}`
  const url = `${API_BASE}${path}`
  return requestUrl(url, endpoint, options)
}

/**
 * URL absoluta (p. ej. health fuera de /api/v1).
 */
async function requestUrl(url, endpointLabel, options = {}) {
  const { headers: optHeaders, body, ...rest } = options
  const headers = {
    ...optHeaders,
  }
  const hasJsonBody = body !== undefined && body !== null
  if (hasJsonBody) {
    headers['Content-Type'] = 'application/json'
  }

  const config = {
    ...rest,
    headers,
  }
  if (hasJsonBody) {
    config.body = typeof body === 'string' ? body : JSON.stringify(body)
  }

  try {
    const response = await fetch(url, config)

    if (response.status === 204) {
      return null
    }

    const text = await response.text()
    let parsed = null
    if (text) {
      try {
        parsed = JSON.parse(text)
      } catch {
        if (!response.ok) {
          throw new ApiError(response.status, text.slice(0, 200), endpointLabel)
        }
        throw new ApiError(response.status, 'Invalid JSON response', endpointLabel)
      }
    }

    if (!response.ok) {
      const msg =
        parsed?.error ||
        parsed?.detail ||
        parsed?.message ||
        `HTTP ${response.status}`
      throw new ApiError(response.status, String(msg), endpointLabel)
    }

    return parsed
  } catch (err) {
    if (err instanceof ApiError) throw err
    throw new ApiError(
      0,
      'Network error — verificar que la API esté corriendo',
      endpointLabel,
    )
  }
}

// --- APIs de dominio (rutas relativas a /api/v1) ---

export const eventsApi = {
  getAll: (params = {}) => {
    const qs = new URLSearchParams(params).toString()
    return request(`/events${qs ? `?${qs}` : ''}`)
  },
  getById: (id) => request(`/events/${encodeURIComponent(id)}`),
  getStats: () => request('/events/stats'),
}

export const identitiesApi = {
  getAll: (params = {}) => {
    const qs = new URLSearchParams(params).toString()
    return request(`/identities${qs ? `?${qs}` : ''}`)
  },
  getById: (id) => request(`/identities/${encodeURIComponent(id)}`),
  getTimeline: (id) => request(`/identities/${encodeURIComponent(id)}/timeline`),
}

export const incidentsApi = {
  getAll: (params = {}) => {
    const qs = new URLSearchParams(params).toString()
    return request(`/incidents${qs ? `?${qs}` : ''}`)
  },
  getById: (id) => request(`/incidents/${encodeURIComponent(id)}`),
  /** La API solo persiste `estado`; comentario reservado para futuras extensiones. */
  updateEstado: (id, estado, _comentario = '') =>
    request(`/incidents/${encodeURIComponent(id)}/estado`, {
      method: 'POST',
      body: { estado },
    }),
}

export const alertsApi = {
  getHoneypots: () => request('/alerts/honeypots'),
  getSummary: () => request('/alerts/summary'),
}

export const aiApi = {
  getMemos: () => request('/ai/memos'),
  analyzeIncident: (id) =>
    request(`/ai/analyze/${encodeURIComponent(id)}`, { method: 'POST' }),
  getCeoView: () => request('/ai/ceo-view', { method: 'POST' }),
}

export const simulatorApi = {
  runScenario: (scenario, target, intensity) =>
    request('/simulator/scenario', {
      method: 'POST',
      body: { scenario, target, intensity },
    }),
  getStatus: () => request('/simulator/status'),
}

export const responseApi = {
  getProposals: (params = {}) => {
    const qs = new URLSearchParams(params).toString()
    return request(`/response/proposals${qs ? `?${qs}` : ''}`)
  },
  approve: (id, comentario = '') =>
    request(`/response/proposals/${encodeURIComponent(id)}/approve`, {
      method: 'POST',
      body: { comentario },
    }),
  reject: (id, motivo) =>
    request(`/response/proposals/${encodeURIComponent(id)}/reject`, {
      method: 'POST',
      body: { motivo },
    }),
}

export const healthApi = {
  /** GET /health/detail (requiere X-Nyxar-Health-Key). */
  getDetail: (healthKey) =>
    requestUrl(`${getServerOrigin()}/health/detail`, '/health/detail', {
      method: 'GET',
      headers: healthKey ? { 'X-Nyxar-Health-Key': healthKey } : {},
    }),
}

export const huntingApi = {
  listHypotheses: async (params = {}) => {
    const q = new URLSearchParams()
    if (params.limit != null) q.set('limit', String(params.limit))
    if (params.offset != null) q.set('offset', String(params.offset))
    const suffix = q.toString() ? `?${q}` : ''
    return request(`/hunting/hypotheses${suffix}`)
  },

  createHypothesis: async ({ descripcion, hunter }) =>
    request('/hunting/hypotheses', {
      method: 'POST',
      body: { descripcion, hunter: hunter || 'analista_manual' },
    }),

  runHunt: async (hypothesisId, iniciadoBy = 'dashboard_analista') => {
    const q = new URLSearchParams({ iniciado_by: iniciadoBy })
    return request(
      `/hunting/hypotheses/${encodeURIComponent(hypothesisId)}/run?${q}`,
      { method: 'POST' },
    )
  },

  listSessions: async (params = {}) => {
    const q = new URLSearchParams()
    if (params.estado) q.set('estado', params.estado)
    if (params.limit != null) q.set('limit', String(params.limit))
    const suffix = q.toString() ? `?${q}` : ''
    return request(`/hunting/sessions${suffix}`)
  },

  getSession: async (sessionId) =>
    request(`/hunting/sessions/${encodeURIComponent(sessionId)}`),
}

export const ceoApi = {
  requestCeoView: () => aiApi.getCeoView(),
}

export const identityApi = {
  get: () => request('/identity'),
}
