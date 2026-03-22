/**
 * Cliente HTTP mínimo para la API NYXAR (mismo origen en prod o proxy Vite en dev).
 */

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
