/**
 * Datos de demo / sintéticos solo en desarrollo (`vite`).
 * En build de producción es false: el front depende del backend/WebSocket.
 */
export const isDevDataEnabled = Boolean(import.meta.env.DEV)
