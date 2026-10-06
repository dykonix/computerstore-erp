import { createContext } from 'react'
import type { AuthenticatedUser } from '../api/authApi'

export interface AuthContextValue {
  user: AuthenticatedUser | null
  loading: boolean
  error: string
  login: (email: string, password: string) => Promise<void>
  logout: () => void
  clearError: () => void
  hasPermission: (permission: string) => boolean
}

export const AuthContext = createContext<AuthContextValue | null>(null)