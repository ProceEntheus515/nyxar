import { create } from 'zustand';

const LS_SIDEBAR = 'nyxar-sidebar-collapsed'

function readSidebarCollapsed() {
  try {
    return localStorage.getItem(LS_SIDEBAR) === '1'
  } catch {
    return false
  }
}

export const useStore = create((set) => ({
  events: [],           // últimos 500 eventos
  identities: {},       // mapa id → Identidad
  incidents: [],        // incidentes abiertos
  alerts: [],           // alertas recientes (fusionando incidentes y honeypots)
  aiMemos: [],          // memos de AI
  stats: {},            // estadísticas generales
  healthReport: null,
  healthThroughput: [],
  healthGeneral: null,
  isLabMode: false,     // modo simulación
  wsConnected: false,
  /** Tras el primer connect real, sirve para distinguir "conectando" vs "reconectando". */
  wsEverConnected: false,
  /** Panel de detalle: persiste al cambiar de vista hasta cerrar. */
  detailPanel: { type: null, id: null, isOpen: false },
  /** Si se setea, Timeline intenta hacer scroll a ese evento y luego se limpia. */
  timelineFocusEventId: null,
  /**
   * ID de nodo interno (misma clave que buildIdentityNodes: IP / id_usuario).
   * NetworkMap hace zoom al nodo y luego limpia el valor.
   */
  mapFocusNodeId: null,
  sidebarCollapsed: readSidebarCollapsed(),
  /** Propuestas de respuesta pendientes (badge en sidebar; WebSocket en futuras iteraciones). */
  responseProposalsPending: 0,

  setTimelineFocusEventId: (id) => set({ timelineFocusEventId: id || null }),

  requestMapFocus: (nodeId) =>
    set({ mapFocusNodeId: nodeId != null && String(nodeId).trim() ? String(nodeId).trim() : null }),

  clearMapFocusRequest: () => set({ mapFocusNodeId: null }),

  setResponseProposalsPending: (n) =>
    set({ responseProposalsPending: Math.max(0, Number(n) || 0) }),

  setWsConnected: (connected) =>
    set((state) => ({
      wsConnected: Boolean(connected),
      wsEverConnected: state.wsEverConnected || Boolean(connected),
    })),

  openDetailPanel: (type, id) =>
    set({
      detailPanel: { type: type || null, id: id ?? null, isOpen: true },
    }),

  closeDetailPanel: () =>
    set((state) => ({
      detailPanel: { ...state.detailPanel, isOpen: false },
    })),

  setSidebarCollapsed: (collapsed) => {
    try {
      localStorage.setItem(LS_SIDEBAR, collapsed ? '1' : '0')
    } catch {
      /* ignore */
    }
    set({ sidebarCollapsed: Boolean(collapsed) })
  },

  addEvent: (event) => set((state) => ({ 
    events: [event, ...state.events].slice(0, 500) 
  })),
  
  addEventBatch: (batch) => set((state) => ({
    events: [...batch, ...state.events].slice(0, 500)
  })),
  
  updateIdentity: (idUpdate) => set((state) => {
     const id = idUpdate.id || idUpdate.identidad_id;
     if (!id) return state;
     const current = state.identities[id] || {};
     return { identities: { ...state.identities, [id]: { ...current, ...idUpdate } } }
  }),
  
  addIncident: (incident) => set((state) => ({ 
    incidents: [incident, ...state.incidents] 
  })),
  
  addAlert: (alert) => set((state) => ({ 
    alerts: [alert, ...state.alerts] 
  })),
  
  addAiMemo: (memo) => set((state) => ({ 
    aiMemos: [memo, ...state.aiMemos] 
  })),
  
  updateStats: (newStats) => set((state) => ({ 
    stats: { ...state.stats, ...newStats } 
  })),

  setHealthReport: (report) =>
    set({
      healthReport: report,
      healthGeneral: report?.estado_general ?? null,
    }),

  setHealthThroughput: (points) => set({ healthThroughput: Array.isArray(points) ? points : [] }),
  
  setLabMode: (mode) => set({ isLabMode: mode }),
  
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
        next.stats = { ...state.stats, ...statsPatch }
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

      return next
    }),
}));
