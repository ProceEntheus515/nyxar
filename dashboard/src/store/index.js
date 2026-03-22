import { create } from 'zustand';

export const useStore = create((set, get) => ({
  events: [],           // últimos 500 eventos
  identities: {},       // mapa id → Identidad
  incidents: [],        // incidentes abiertos
  alerts: [],           // alertas recientes (fusionando incidentes y honeypots)
  aiMemos: [],          // memos de AI
  stats: {},            // estadísticas generales
  isLabMode: false,     // modo simulación
  /** Si se setea, Timeline intenta hacer scroll a ese evento y luego se limpia. */
  timelineFocusEventId: null,

  setTimelineFocusEventId: (id) => set({ timelineFocusEventId: id || null }),

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
  
  setLabMode: (mode) => set({ isLabMode: mode }),
  
  setInitialState: ({ last_events, risk_identities, ai_memos }) => set((state) => {
     const idsMap = (risk_identities || []).reduce((acc, curr) => ({...acc, [curr.id]: curr}), {});
     return {
       events: last_events || [],
       identities: { ...state.identities, ...idsMap },
       aiMemos: ai_memos || []
     };
  })
}));
