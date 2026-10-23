import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError, isAbortError, newRequestId, request } from './http'

const fetchMock = vi.fn()

function json(body: unknown, init: ResponseInit = {}): Response {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
    ...init,
  })
}

beforeEach(() => {
  fetchMock.mockReset()
  vi.stubGlobal('fetch', fetchMock)
})

afterEach(() => {
  vi.unstubAllGlobals()
  vi.useRealTimers()
})

describe('request', () => {
  it('builds the URL, omits empty query values and sends a valid X-Request-ID', async () => {
    fetchMock.mockResolvedValue(json({ ok: true }))

    await request('GET', '/api/v1/jobs', {
      query: { limit: 20, offset: 0, status: undefined, empty: '', nothing: null },
    })

    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit]
    expect(url).toBe('http://localhost:8000/api/v1/jobs?limit=20&offset=0')
    const headers = init.headers as Record<string, string>
    expect(headers['X-Request-ID']).toMatch(/^[A-Za-z0-9._-]{8,64}$/)
    expect(headers.Accept).toBe('application/json')
    expect(init.body).toBeUndefined()
  })

  it('sends JSON bodies with Content-Type', async () => {
    fetchMock.mockResolvedValue(json({ id: '1' }, { status: 201 }))

    const result = await request<{ id: string }>('POST', '/api/v1/jobs', { body: { title: 'x' } })

    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit]
    expect(init.body).toBe('{"title":"x"}')
    expect((init.headers as Record<string, string>)['Content-Type']).toBe('application/json')
    expect(result).toEqual({ id: '1' })
  })

  it('returns undefined for 204', async () => {
    fetchMock.mockResolvedValue(new Response(null, { status: 204 }))
    await expect(request('DELETE', '/api/v1/jobs/1')).resolves.toBeUndefined()
  })

  it('maps the backend error envelope to ApiError', async () => {
    fetchMock.mockResolvedValue(
      json(
        { error: { code: 'JOB_NOT_FOUND', message: 'Job not found', details: null, request_id: 'body-id' } },
        { status: 404, headers: { 'X-Request-ID': 'header-id-123' } },
      ),
    )

    const error = await request('GET', '/api/v1/jobs/x').catch((e: unknown) => e)

    expect(error).toBeInstanceOf(ApiError)
    expect(error).toMatchObject({
      status: 404,
      code: 'JOB_NOT_FOUND',
      message: 'Job not found',
      requestId: 'header-id-123',
    })
  })

  it('handles non-JSON error bodies (e.g. a proxy error page)', async () => {
    fetchMock.mockResolvedValue(new Response('<html>Bad gateway</html>', { status: 502 }))
    const error = await request('GET', '/x').catch((e: unknown) => e)
    expect(error).toMatchObject({ status: 502, code: 'HTTP_502' })
  })

  it('turns network failures into NETWORK_ERROR (status 0)', async () => {
    fetchMock.mockRejectedValue(new TypeError('Failed to fetch'))
    const error = await request('GET', '/x').catch((e: unknown) => e)
    expect(error).toBeInstanceOf(ApiError)
    expect(error).toMatchObject({ status: 0, code: 'NETWORK_ERROR' })
  })

  it('rethrows caller aborts as AbortError, not as an API failure', async () => {
    fetchMock.mockImplementation(
      (_url: string, init: RequestInit) =>
        new Promise((_resolve, reject) => {
          init.signal?.addEventListener('abort', () => reject(new DOMException('Aborted', 'AbortError')))
        }),
    )
    const controller = new AbortController()
    const pending = request('GET', '/x', { signal: controller.signal }).catch((e: unknown) => e)
    controller.abort()
    const error = await pending
    expect(isAbortError(error)).toBe(true)
    expect(error).not.toBeInstanceOf(ApiError)
  })

  it('times out hanging requests', async () => {
    vi.useFakeTimers()
    fetchMock.mockImplementation(
      (_url: string, init: RequestInit) =>
        new Promise((_resolve, reject) => {
          init.signal?.addEventListener('abort', () => reject(new DOMException('Aborted', 'AbortError')))
        }),
    )
    const pending = request('GET', '/x', { timeoutMs: 50 }).catch((e: unknown) => e)
    await vi.advanceTimersByTimeAsync(60)
    expect(await pending).toMatchObject({ status: 0, code: 'TIMEOUT' })
  })
})

describe('newRequestId', () => {
  it('falls back when crypto.randomUUID is unavailable (non-secure contexts)', () => {
    vi.stubGlobal('crypto', {})
    expect(newRequestId()).toMatch(/^[A-Za-z0-9._-]{8,64}$/)
  })
})
