export const MOCK_DATA = {
  last_events: [
    { id: "M1", source: "firewall", timestamp: new Date().toISOString(), interno: { ip: "192.168.1.55", area: "Finanzas" }, externo: { valor: "185.10.99.1" }, enrichment: { risk_score: 85 } },
    { id: "M2", source: "dns", timestamp: new Date(Date.now() - 40000).toISOString(), interno: { ip: "192.168.1.12", area: "IT" }, externo: { valor: "github.com" }, enrichment: { risk_score: 10 } },
    { id: "M3", source: "proxy", timestamp: new Date(Date.now() - 250000).toISOString(), interno: { ip: "192.168.1.55", area: "Finanzas" }, externo: { valor: "mega.nz" }, enrichment: { risk_score: 65 } },
    { id: "M4", source: "wazuh", timestamp: new Date(Date.now() - 150000).toISOString(), interno: { ip: "192.168.1.34", area: "Gerencia" }, externo: { valor: "0.0.0.0" }, enrichment: { risk_score: 95 } }
  ],
  risk_identities: [
    { id: "192.168.1.55", ip_asociada: "192.168.1.55", nombre_completo: "Laura Finanzas", area: "Finanzas", risk_score: 85, delta_2h: 40, dispositivo: "PC-FIN-01", hostname: "fin-pc-01", last_seen_ts: new Date().toISOString() },
    { id: "192.168.1.12", ip_asociada: "192.168.1.12", nombre_completo: "Admin Sys", area: "IT", risk_score: 10, delta_2h: -2, dispositivo: "MAC-IT", hostname: "sys-admin-mac", last_seen_ts: new Date().toISOString() },
    { id: "192.168.1.34", ip_asociada: "192.168.1.34", nombre_completo: "Emilio CEO", area: "Gerencia", risk_score: 95, delta_2h: 80, dispositivo: "MOBILE-CEO", hostname: "iphone-emilio", last_seen_ts: new Date().toISOString() },
    { id: "192.168.1.88", ip_asociada: "192.168.1.88", nombre_completo: "Marcos Ventas", area: "Ventas", risk_score: 35, delta_2h: 5, dispositivo: "TAB-VEN", hostname: "tablet-04", last_seen_ts: new Date().toISOString() }
  ],
  ai_memos: []
};
