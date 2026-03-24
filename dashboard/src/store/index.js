import { create } from 'zustand'
import { subscribeWithSelector } from 'zustand/middleware'

const MAX_EVENTS = 500

const LS_SIDEBAR = 'nyxar-sidebar-collapsed'

function readSidebarCollapsed() {
  try {
    return localStorage.getItem(LS_SIDEBAR) === '1'
  } catch {
    return false
  }
}

const defaultStats = {
  eventos_por_min: 0,
  identidades_activas: 0,
  alertas_abiertas: 0,
  honeypots_hoy: 0,
}

function riskScoreFromEvent(ev) {
  if (ev == null) return 0
  const top = Number(ev.risk_score)
  if (Number.isFinite(top)) return top
  const nested = Number(ev.enrichment?.risk_score)
  return Number.isFinite(nested) ? nested : 0
}

export const useStore = create(
  subscribeWithSelector((set, get) => {
    const setWsConnection = (connected) =>
      set((state) => ({
        wsConnected: Boolean(connected),
        wsEverConnected: state.wsEverConnected || Boolean(connected),
      }))

    return {
      events: [],
      identities: {},
      incidents: [],
      alerts: [],
      honeypotHits: [],
      aiMemos: [],
      ceoAnalyses: [],
      stats: { ...defaultStats },
      healthReport: null,
      healthThroughput: [],
      healthGeneral: null,
      systemHealth: null,
      isLabMode: import.meta.env.VITE_LAB_MODE === 'true',
      wsConnected: false,
      wsEverConnected: false,
      detailPanel: { type: null, id: null, isOpen: false },
      timelineFocusEventId: null,
      mapFocusNodeId: null,
      identityBaselines: {},
      huntingIdentityIds: [],
      huntingSessionIdentityIds: [],
      sidebarCollapsed: readSidebarCollapsed(),
      responseProposalsPending: 0,
      proposals: [],

      timelineFilters: {
        source: null,
        minSeverity: null,
        area: null,
        onlyAlerts: false,
      },

      setTimelineFocusEventId: (id) => set({ timelineFocusEventId: id || null }),

      requestMapFocus: (nodeId) =>
        set({
          mapFocusNodeId:
            nodeId != null && String(nodeId).trim() ? String(nodeId).trim() : null,
        }),

      clearMapFocusRequest: () => set({ mapFocusNodeId: null }),

      setHuntingSessionIdentityIds: (ids) =>
        set({
          huntingSessionIdentityIds: Array.isArray(ids)
            ? ids.map((x) => String(x).trim()).filter(Boolean)
            : [],
        }),

      setResponseProposalsPending: (n) =>
        set({ responseProposalsPending: Math.max(0, Number(n) || 0) }),

      setWsConnected: setWsConnection,
      setConnected: setWsConnection,

      openDetailPanel: (type, id) =>
        set({
          detailPanel: { type: type || null, id: id ?? null, isOpen: true },
        }),

      closeDetailPanel: () =>
        set((state) => ({
          detailPanel: { ...state.detailPanel, isOpen: false },
        })),

      openDetail: (type, id) =>
        set({
          detailPanel: { type: type || null, id: id ?? null, isOpen: true },
        }),

      closeDetail: () =>
        set({ detailPanel: { isOpen: false, type: null, id: null } }),

      setSidebarCollapsed: (collapsed) => {
        try {
          localStorage.setItem(LS_SIDEBAR, collapsed ? '1' : '0')
        } catch {
          /* ignore */
        }
        set({ sidebarCollapsed: Boolean(collapsed) })
      },

      addEvent: (event) =>
        set((state) => ({
          events: [event, ...state.events].slice(0, MAX_EVENTS),
        })),

      addEventBatch: (batch) =>
        set((state) => ({
          events: [...(Array.isArray(batch) ? batch : []), ...state.events].slice(0, MAX_EVENTS),
        })),

      addEvents: (newEvents) =>
        set((state) => ({
          events: [...(Array.isArray(newEvents) ? newEvents : []), ...state.events].slice(
            0,
            MAX_EVENTS,
          ),
        })),

      setIdentities: (identities) => {
        const map = {}
        ;(Array.isArray(identities) ? identities : []).forEach((row) => {
          if (row?.id) map[row.id] = row
        })
        set({ identities: map })
      },

      updateIdentity: (idUpdate) =>
        set((state) => {
          const id = idUpdate?.id || idUpdate?.identidad_id
          if (!id) return state
          const current = state.identities[id] || {}
          const nextRow = {
            ...current,
            ...idUpdate,
            ...(idUpdate.risk_score != null ? { risk_score_actual: idUpdate.risk_score } : {}),
            ...(idUpdate.delta != null ? { _delta: idUpdate.delta } : {}),
          }
          return { identities: { ...state.identities, [id]: nextRow } }
        }),

      addIncident: (incident) =>
        set((state) => ({
          incidents: [incident, ...state.incidents].slice(0, 100),
        })),

      setIncidents: (incidents) =>
        set({ incidents: Array.isArray(incidents) ? incidents : [] }),

      updateIncidentEstado: (id, estado) =>
        set((state) => ({
          incidents: state.incidents.map((inc) =>
            inc.id === id ? { ...inc, estado } : inc,
          ),
        })),

      addAlert: (alert) =>
        set((state) => ({
          alerts: [alert, ...state.alerts],
        })),

      addHoneypotHit: (hit) =>
        set((state) => ({
          alerts: [hit, ...state.alerts],
          honeypotHits: [hit, ...state.honeypotHits].slice(0, 50),
        })),

      addProposal: (proposal) =>
        set((state) => {
          if (proposal == null || typeof proposal !== 'object') {
            return { responseProposalsPending: state.responseProposalsPending + 1 }
          }
          return {
            proposals: [proposal, ...state.proposals],
            responseProposalsPending: state.responseProposalsPending + 1,
          }
        }),

      setProposals: (list) => set({ proposals: Array.isArray(list) ? list : [] }),

      addAiMemo: (memo) =>
        set((state) => ({
          aiMemos: [memo, ...state.aiMemos].slice(0, 50),
        })),

      setAiMemos: (memos) => set({ aiMemos: Array.isArray(memos) ? memos : [] }),

      addCeoAnalysis: (analysis) =>
        set((state) => {
          if (!analysis?.id) return state
          const rest = state.ceoAnalyses.filter((a) => a.id !== analysis.id)
          return { ceoAnalyses: [analysis, ...rest].slice(0, 24) }
        }),

      updateStats: (newStats) =>
        set((state) => ({
          stats: { ...defaultStats, ...state.stats, ...newStats },
        })),

      updateHealth: (health) => set({ systemHealth: health }),

      setHealthReport: (report) =>
        set({
          healthReport: report,
          healthGeneral: report?.estado_general ?? null,
        }),

      setHealthThroughput: (points) =>
        set({ healthThroughput: Array.isArray(points) ? points : [] }),

      setLabMode: (mode) => set({ isLabMode: mode }),

      setTimelineFilter: (key, value) =>
        set((state) => ({
          timelineFilters: { ...state.timelineFilters, [key]: value },
        })),

      getFilteredTimelineEvents: () => {
        const { events, timelineFilters } = get()
        return (events || []).filter((ev) => {
          if (timelineFilters.source && ev.source !== timelineFilters.source) return false
          if (timelineFilters.area && ev.interno?.area !== timelineFilters.area) return false
          const score = riskScoreFromEvent(ev)
          if (timelineFilters.minSeverity != null && score < timelineFilters.minSeverity) {
            return false
          }
          if (timelineFilters.onlyAlerts && score < 60) return false
          return true
        })
      },

      setInitialState: (payload = {}) =>
        set((state) => {
          const {
            last_events,
            risk_identities,
            ai_memos,
            stats: statsPatch,
            alerts: alertsList,
            incidents: incidentsList,
            health_report,
            health_throughput,
            identity_baselines,
            hunting_identity_ids,
            ceo_analyses,
          } = payload

          const idsMap = (risk_identities || []).reduce(
            (acc, curr) => ({ ...acc, [curr.id]: curr }),
            {},
          )

          const next = {
            events: Array.isArray(last_events) ? last_events : state.events,
            identities: { ...state.identities, ...idsMap },
            aiMemos: Array.isArray(ai_memos) ? ai_memos : state.aiMemos,
          }

          if (statsPatch != null && typeof statsPatch === 'object') {
            next.stats = { ...defaultStats, ...state.stats, ...statsPatch }
          }
          if (Array.isArray(alertsList)) {
            next.alerts = alertsList
          }
          if (Array.isArray(incidentsList)) {
            next.incidents = incidentsList
          }
          if (health_report != null) {
            next.healthReport = health_report
            next.healthGeneral = health_report.estado_general ?? null
          }
          if (Array.isArray(health_throughput)) {
            next.healthThroughput = health_throughput
          }
          if (identity_baselines != null && typeof identity_baselines === 'object') {
            next.identityBaselines = { ...state.identityBaselines, ...identity_baselines }
          }
          if (Array.isArray(hunting_identity_ids)) {
            next.huntingIdentityIds = hunting_identity_ids.map(String)
          }
          if (Array.isArray(ceo_analyses)) {
            next.ceoAnalyses = ceo_analyses
          }

          return next
        }),
    }
  }),
)
