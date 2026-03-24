import React, { useEffect, useState } from 'react'
import { BrowserRouter } from 'react-router-dom'
import { useStore } from './store'
import { getAccessToken, setSessionAuth, clearSessionAuth } from './api/session'
import {
  isDevLoginBypassEnabled,
  isNyxarDevBypassToken,
  NYXAR_DEV_BYPASS_TOKEN,
} from './config/devAuth'
import LoginView from './views/LoginView'
import AppWithSocket from './components/auth/AppWithSocket'

function readInitialToken() {
  const stored = getAccessToken()
  if (stored) return stored
  if (isDevLoginBypassEnabled()) {
    setSessionAuth(NYXAR_DEV_BYPASS_TOKEN, 'dev')
    return NYXAR_DEV_BYPASS_TOKEN
  }
  return null
}

export default function App() {
  const [token, setToken] = useState(() => readInitialToken())

  useEffect(() => {
    const onExpire = () => {
      if (isDevLoginBypassEnabled() && isNyxarDevBypassToken(getAccessToken())) {
        return
      }
      clearSessionAuth()
      setToken(null)
    }
    window.addEventListener('nyxar:session-expired', onExpire)
    return () => window.removeEventListener('nyxar:session-expired', onExpire)
  }, [])

  useEffect(() => {
    if (!import.meta.env.DEV) return
    if (!token) return
    const t = setTimeout(() => {
      const state = useStore.getState()
      console.group('=== Verificación del Store (I07) ===')
      console.log('Conectado (WS):', state.wsConnected)
      console.log('Eventos cargados:', state.events.length)
      console.log('Identidades cargadas:', Object.keys(state.identities).length)
      console.log('Incidentes:', state.incidents.length)
      console.log('AI Memos:', state.aiMemos.length)
      console.log('Lab mode:', state.isLabMode)

      if (state.events.length === 0) {
        console.warn('Sin eventos: revisar WebSocket y GET /events')
      }
      if (Object.keys(state.identities).length === 0) {
        console.warn('Sin identidades: revisar GET /identities')
      }
      console.groupEnd()
    }, 3000)
    return () => clearTimeout(t)
  }, [token])

  if (!token) {
    return (
      <LoginView
        onSuccess={(data) => {
          setSessionAuth(data.access_token, data.role)
          setToken(data.access_token)
        }}
      />
    )
  }

  return (
    <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <AppWithSocket token={token} />
    </BrowserRouter>
  )
}
