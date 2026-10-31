import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import { authApi, type AuthInput, type AuthUser } from '../services/authApi'
import { clearAccessToken } from '../services/authSession'
import { onUnauthorized } from '../services/http'

type AuthState = { status: 'checking' | 'guest' | 'authenticated'; user: AuthUser | null }
interface AuthContextValue extends AuthState {
  login: (input: AuthInput) => Promise<void>
  logout: () => Promise<void>
}
const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>(() => ({
    status: authApi.hasSession() ? 'checking' : 'guest',
    user: null,
  }))

  useEffect(() => {
    let mounted = true
    const unsubscribe = onUnauthorized(() => {
      if (mounted) setState({ status: 'guest', user: null })
    })
    if (authApi.hasSession()) {
      void authApi.me().then(
        user => { if (mounted) setState({ status: 'authenticated', user }) },
        () => {
          clearAccessToken()
          if (mounted) setState({ status: 'guest', user: null })
        },
      )
    }
    return () => { mounted = false; unsubscribe() }
  }, [])

  async function login(input: AuthInput) {
    setState({ status: 'checking', user: null })
    try {
      const user = await authApi.login(input)
      setState({ status: 'authenticated', user })
    } catch (error) {
      setState({ status: 'guest', user: null })
      throw error
    }
  }

  async function logout() {
    setState({ status: 'guest', user: null })
    await authApi.logout()
  }

  return <AuthContext.Provider value={{ ...state, login, logout }}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth must be used inside AuthProvider')
  return context
}
