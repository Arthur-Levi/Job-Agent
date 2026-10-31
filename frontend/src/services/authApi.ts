import { clearAccessToken, getAccessToken, setAccessToken } from './authSession'
import { request } from './http'

export interface AuthUser {
  id: string
  name: string
  email: string
}

export interface AuthInput {
  email: string
  password: string
}

export interface RegisterInput extends AuthInput {
  name: string
}

interface TokenResponse {
  access_token: string
  token_type: 'bearer'
}

export const authApi = {
  register: (payload: RegisterInput): Promise<AuthUser> =>
    request<AuthUser>('POST', '/api/v1/auth/register', { body: payload }),

  async login(payload: AuthInput): Promise<AuthUser> {
    // Clear prior identity before switching accounts.
    clearAccessToken()
    const token = await request<TokenResponse>('POST', '/api/v1/auth/login', { body: payload })
    if (token.token_type !== 'bearer') {
      throw new Error('Unexpected authentication response')
    }
    setAccessToken(token.access_token)
    try {
      return await request<AuthUser>('GET', '/api/v1/auth/me')
    } catch (error) {
      clearAccessToken()
      throw error
    }
  },

  me: (): Promise<AuthUser> =>
    request<AuthUser>('GET', '/api/v1/auth/me'),

  async logout(): Promise<void> {
    if (!getAccessToken()) return
    try {
      await request<void>('POST', '/api/v1/auth/logout')
    } finally {
      // Fail closed locally even when the server is unreachable.
      clearAccessToken()
    }
  },

  hasSession: (): boolean => Boolean(getAccessToken()),
}
