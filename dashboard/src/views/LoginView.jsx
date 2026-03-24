import { useState } from 'react'
import { authApi, ApiError } from '../api/client'
import styles from './LoginView.module.css'

export default function LoginView({ onSuccess }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const data = await authApi.login(username.trim(), password)
      const token = data?.access_token
      if (!token) {
        setError('Respuesta inválida del servidor.')
        return
      }
      onSuccess({
        access_token: token,
        role: data?.role ?? '',
      })
    } catch (err) {
      const msg =
        err instanceof ApiError
          ? err.message
          : 'No se pudo conectar con la API. Verificá URL y que el servicio esté en marcha.'
      setError(msg)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className={styles.screen}>
      <div className={styles.card}>
        <h1 className={styles.title}>NYXAR</h1>
        <p className={styles.subtitle}>Iniciá sesión para abrir el dashboard de operaciones.</p>
        <form className={styles.form} onSubmit={handleSubmit}>
          <label className={styles.label}>
            Usuario
            <input
              className={styles.input}
              name="username"
              autoComplete="username"
              value={username}
              onChange={(ev) => setUsername(ev.target.value)}
              disabled={loading}
              required
            />
          </label>
          <label className={styles.label}>
            Contraseña
            <input
              className={styles.input}
              name="password"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(ev) => setPassword(ev.target.value)}
              disabled={loading}
              required
            />
          </label>
          {error ? (
            <p className={styles.error} role="alert">
              {error}
            </p>
          ) : null}
          <button className={styles.submit} type="submit" disabled={loading}>
            {loading ? 'Entrando…' : 'Entrar'}
          </button>
        </form>
      </div>
    </div>
  )
}
