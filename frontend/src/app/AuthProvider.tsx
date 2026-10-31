import { useEffect, useState, type ReactNode } from 'react'
import { authApi, type AuthInput } from '../services/authApi'
import { clearAccessToken, getAccessToken } from '../services/authSession'
import { onUnauthorized } from '../services/http'
import { AuthContext, type AuthState } from './authContext'

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
    const originalToken = getAccessToken()
    if (originalToken) {
      void authApi.me().then(
        user => {
          if (mounted && getAccessToken() === originalToken) setState({ status: 'authenticated', user })
        },
        () => {
          if (getAccessToken() !== originalToken) return
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
