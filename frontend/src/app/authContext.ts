import { createContext, useContext } from 'react'
import type { AuthInput, AuthUser } from '../services/authApi'

export type AuthState = {
  status: 'checking' | 'guest' | 'authenticated'
  user: AuthUser | null
}

export interface AuthContextValue extends AuthState {
  login: (input: AuthInput) => Promise<void>
  logout: () => Promise<void>
}

export const AuthContext = createContext<AuthContextValue | null>(null)

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth must be used inside AuthProvider')
  return context
}
