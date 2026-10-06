import { useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import { fetchCurrentUser, login as requestLogin } from '../api/authApi'
import type { AuthenticatedUser } from '../api/authApi'
import { AuthContext } from './AuthContext'

const TOKEN_KEY = 'computerstore_access_token'

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthenticatedUser | null>(null)
  const [loading, setLoading] = useState(() => Boolean(window.localStorage.getItem(TOKEN_KEY)))
  const [error, setError] = useState('')

  useEffect(() => {
    const accessToken = window.localStorage.getItem(TOKEN_KEY)
    if (!accessToken) return

    let cancelled = false
    void fetchCurrentUser(accessToken)
      .then((currentUser) => {
        if (!cancelled) setUser(currentUser)
      })
      .catch(() => {
        window.localStorage.removeItem(TOKEN_KEY)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => { cancelled = true }
  }, [])

  async function login(email: string, password: string) {
    setError('')
    try {
      const tokenResponse = await requestLogin(email, password)
      window.localStorage.setItem(TOKEN_KEY, tokenResponse.access_token)
      const currentUser = await fetchCurrentUser(tokenResponse.access_token)
      setUser(currentUser)
    } catch (loginError) {
      window.localStorage.removeItem(TOKEN_KEY)
      setUser(null)
      const message = loginError instanceof Error ? loginError.message : ''
      setError(message === 'Invalid email or password' ? message : 'Unable to sign in. Check your credentials and try again.')
      throw loginError
    }
  }

  function logout() {
    window.localStorage.removeItem(TOKEN_KEY)
    setUser(null)
    setError('')
  }

  function clearError() {
    setError('')
  }

  function hasPermission(permission: string) {
    return Boolean(user?.permissions.includes(permission))
  }

  return (
    <AuthContext.Provider value={{ user, loading, error, login, logout, clearError, hasPermission }}>
      {children}
    </AuthContext.Provider>
  )
}