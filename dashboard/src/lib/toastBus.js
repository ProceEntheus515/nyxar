/**
 * Bus mínimo para toasts (I09): sin dependencias; usable desde hooks y desde useWebSocket.
 */

let toasts = []
const listeners = new Set()

function emit() {
  listeners.forEach((fn) => {
    try {
      fn()
    } catch {
      /* ignore */
    }
  })
}

export function subscribeToasts(listener) {
  listeners.add(listener)
  return () => listeners.delete(listener)
}

export function getToastSnapshot() {
  return toasts
}

function dismissToast(id) {
  toasts = toasts.filter((t) => t.id !== id)
  emit()
}

/**
 * @param {{ type?: string, title: string, message: string }} payload
 */
export function showToast(payload) {
  const id = `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`
  const toast = {
    id,
    type: payload.type || 'info',
    title: payload.title || '',
    message: payload.message || '',
  }
  toasts = [toast, ...toasts].slice(0, 5)
  emit()
  window.setTimeout(() => dismissToast(id), 6500)
}

export { dismissToast }
