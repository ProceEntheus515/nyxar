import { useWebSocket } from '../../hooks/useWebSocket'
import AppRoutes from './AppRoutes'

/**
 * Rutas autenticadas + WebSocket con JWT en el handshake.
 */
export default function AppWithSocket({ token }) {
  useWebSocket(token)
  return <AppRoutes />
}
