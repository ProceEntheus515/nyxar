/**
 * Bypass opcional del login solo en desarrollo (Vite).
 * No usar en producción: el build de prod no debe exponer VITE_DEV_SKIP_LOGIN.
 */

export const NYXAR_DEV_BYPASS_TOKEN = '__nyxar_dev_ui_bypass__'

export function isDevLoginBypassEnabled() {
  return import.meta.env.DEV && import.meta.env.VITE_DEV_SKIP_LOGIN === 'true'
}

export function isNyxarDevBypassToken(token) {
  return typeof token === 'string' && token === NYXAR_DEV_BYPASS_TOKEN
}
