import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { authApi } from './authApi'
import { clearAccessToken, getAccessToken, setAccessToken } from './authSession'

const fetchMock = vi.fn()

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

beforeEach(() => {
  clearAccessToken()
  fetchMock.mockReset()
  vi.stubGlobal('fetch', fetchMock)
})

afterEach(() => {
  clearAccessToken()
  vi.unstubAllGlobals()
})

describe('authenticated HTTP transport', () => {
  it('does not attach Authorization without a session', async () => {
    fetchMock.mockResolvedValue(json({ items: [] }))
    await authApi.register({ name: 'Test Candidate', email: 'candidate@example.com', password: 'test-only-pass-123!' })
    const headers = fetchMock.mock.calls[0][1].headers as Record<string, string>
    expect(headers.Authorization).toBeUndefined()
  })

  it('login establishes session after /me confirms identity and attaches Bearer to subsequent requests', async () => {
    fetchMock
      .mockResolvedValueOnce(json({ access_token: 'a'.repeat(64), token_type: 'bearer' }))
      .mockResolvedValueOnce(json({ id: 'uuid-1', name: 'Lucas', email: 'lucas@example.com' }))
      .mockResolvedValueOnce(json({ id: 'uuid-1', name: 'Lucas', email: 'lucas@example.com' }))

    const user = await authApi.login({ email: 'lucas@example.com', password: 'test-password-12345' })
    expect(user.name).toBe('Lucas')
    expect(authApi.hasSession()).toBe(true)
    expect(getAccessToken()).toBe('a'.repeat(64))
    expect((fetchMock.mock.calls[0][1].headers as Record<string, string>).Authorization).toBeUndefined()
    expect((fetchMock.mock.calls[1][1].headers as Record<string, string>).Authorization).toBe('Bearer ' + 'a'.repeat(64))
    await authApi.me()
    expect((fetchMock.mock.calls[2][1].headers as Record<string, string>).Authorization).toBe('Bearer ' + 'a'.repeat(64))
  })

  it('does not retain token when /me verification fails after login', async () => {
    fetchMock
      .mockResolvedValueOnce(json({ access_token: 'b'.repeat(64), token_type: 'bearer' }))
      .mockResolvedValueOnce(json({ error: { code: 'HTTP_401', message: 'Unauthorized' } }, 401))
    await expect(authApi.login({ email: 'x@example.com', password: 'test-only-password' })).rejects.toMatchObject({ status: 401 })
    expect(getAccessToken()).toBeNull()
  })

  it('logout clears local token even when server is unreachable', async () => {
    setAccessToken('c'.repeat(64))
    fetchMock.mockRejectedValueOnce(new TypeError('Network failed'))
    await expect(authApi.logout()).rejects.toMatchObject({ code: 'NETWORK_ERROR' })
    expect(getAccessToken()).toBeNull()
  })

  it('logout successfully revokes remote session and clears local token', async () => {
    setAccessToken('d'.repeat(64))
    fetchMock.mockResolvedValueOnce(new Response(null, { status: 204 }))
    await authApi.logout()
    expect((fetchMock.mock.calls[0][1].headers as Record<string, string>).Authorization).toBe('Bearer ' + 'd'.repeat(64))
    expect(getAccessToken()).toBeNull()
  })

  it('refuses invalid tokens', () => {
    expect(() => setAccessToken('short')).toThrow()
    expect(getAccessToken()).toBeNull()
  })
})
