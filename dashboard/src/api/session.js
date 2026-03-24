const TOKEN_KEY = 'nyxar_access_token'
const ROLE_KEY = 'nyxar_role'

export function getAccessToken() {
  try {
    return sessionStorage.getItem(TOKEN_KEY)
  } catch {
    return null
  }
}

export function getStoredRole() {
  try {
    return sessionStorage.getItem(ROLE_KEY)
  } catch {
    return null
  }
}

export function setSessionAuth(accessToken, role) {
  try {
    sessionStorage.setItem(TOKEN_KEY, accessToken)
    if (role != null && role !== '') {
      sessionStorage.setItem(ROLE_KEY, String(role))
    }
  } catch {
    /* ignore quota / private mode */
  }
}

export function clearSessionAuth() {
  try {
    sessionStorage.removeItem(TOKEN_KEY)
    sessionStorage.removeItem(ROLE_KEY)
  } catch {
    /* ignore */
  }
}
