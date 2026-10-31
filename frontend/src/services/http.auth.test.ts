import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { clearAccessToken, getAccessToken, setAccessToken } from './authSession'
import { onUnauthorized, request } from './http'

const fetchMock = vi.fn()
beforeEach(() => {
  clearAccessToken()
  fetchMock.mockReset()
  vi.stubGlobal('fetch', fetchMock)
})
afterEach(() => {
  clearAccessToken()
  vi.unstubAllGlobals()
})

describe('fail-closed authentication transport', () => {
  it('revokes the active memory token and notifies on protected 401', async () => {
    const listener = vi.fn()
    const unsubscribe = onUnauthorized(listener)
    setAccessToken('a'.repeat(64))
    fetchMock.mockResolvedValueOnce(new Response('Unauthorized', { status: 401 }))
    await expect(request('GET', '/api/v1/auth/me')).rejects.toMatchObject({ status: 401 })
    expect(getAccessToken()).toBeNull()
    expect(listener).toHaveBeenCalledOnce()
    unsubscribe()
  })

  it('does not clear a newer session when an older request receives a delayed 401', async () => {
    setAccessToken('a'.repeat(64))
    const deferred = { resolve: (_value: Response) => {} }
    fetchMock.mockImplementationOnce(() => new Promise<Response>(resolve => { deferred.resolve = resolve }))
    const first = request('GET', '/api/v1/jobs').catch((error: unknown) => error)
    setAccessToken('b'.repeat(64))
    deferred.resolve(new Response('Unauthorized', { status: 401 }))
    await expect(first).resolves.toMatchObject({ status: 401 })
    expect(getAccessToken()).toBe('b'.repeat(64))
  })

  it('never stores the bearer token persistently', () => {
    setAccessToken('c'.repeat(64))
    expect(window.localStorage.length).toBe(0)
    expect(window.sessionStorage.length).toBe(0)
  })
})
