import { clearAccessToken, getAccessToken } from './authSession'

const unauthorizedListeners = new Set<() => void>()

export function onUnauthorized(listener: () => void): () => void {
  unauthorizedListeners.add(listener)
  return () => { unauthorizedListeners.delete(listener) }
}

export type Query = Record<string, string | number | boolean | null | undefined>

export interface ApiErrorInit {
  status: number
  code: string
  message: string
  details?: unknown
  requestId?: string | null
}

/** Erro padronizado do cliente. status 0 = falha antes de haver resposta HTTP. */
export class ApiError extends Error {
  readonly status: number
  readonly code: string
  readonly details: unknown
  readonly requestId: string | null

  constructor(init: ApiErrorInit) {
    super(init.message)
    this.name = 'ApiError'
    this.status = init.status
    this.code = init.code
    this.details = init.details ?? null
    this.requestId = init.requestId ?? null
  }
}

export const REQUEST_ID_HEADER = 'X-Request-ID'
const DEFAULT_TIMEOUT_MS = 15_000

export function getBaseUrl(): string {
  return (import.meta.env.VITE_API_URL ?? 'http://localhost:8000').replace(/\/+$/, '')
}

/** Aceito pelo backend: [A-Za-z0-9._-]{8,64}. randomUUID só existe em contexto seguro. */
export function newRequestId(): string {
  const uuid = globalThis.crypto?.randomUUID?.()
  if (uuid) return uuid
  return `req-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 12)}`
}

export function isAbortError(error: unknown): boolean {
  return error instanceof DOMException && error.name === 'AbortError'
}

function buildUrl(path: string, query?: Query): string {
  const url = new URL(`${getBaseUrl()}${path}`)
  for (const [key, value] of Object.entries(query ?? {})) {
    if (value !== undefined && value !== null && value !== '') {
      url.searchParams.set(key, String(value))
    }
  }
  return url.toString()
}

interface ErrorEnvelope {
  error?: { code?: string; message?: string; details?: unknown; request_id?: string | null }
}

function toApiError(response: Response, text: string): ApiError {
  let envelope: ErrorEnvelope | null = null
  try {
    envelope = text ? (JSON.parse(text) as ErrorEnvelope) : null
  } catch {
    envelope = null // corpo não-JSON (ex.: página de erro de um proxy)
  }
  const body = envelope?.error
  return new ApiError({
    status: response.status,
    code: body?.code ?? `HTTP_${response.status}`,
    message: body?.message ?? `Request failed (${response.status})`,
    details: body?.details,
    requestId: response.headers.get(REQUEST_ID_HEADER) ?? body?.request_id ?? null,
  })
}

export interface RequestOptions {
  query?: Query
  body?: unknown
  signal?: AbortSignal
  timeoutMs?: number
}

export async function request<T>(
  method: 'GET' | 'POST' | 'PATCH' | 'DELETE',
  path: string,
  options: RequestOptions = {},
): Promise<T> {
  const requestId = newRequestId()
  const controller = new AbortController()
  const { signal: callerSignal } = options
  const forwardAbort = () => controller.abort()
  if (callerSignal?.aborted) controller.abort()
  callerSignal?.addEventListener('abort', forwardAbort)
  let timedOut = false
  const timer = setTimeout(() => {
    timedOut = true
    controller.abort()
  }, options.timeoutMs ?? DEFAULT_TIMEOUT_MS)

  try {
    const headers: Record<string, string> = { Accept: 'application/json', [REQUEST_ID_HEADER]: requestId }
    const token = getAccessToken()
    if (token) headers.Authorization = `Bearer ${token}`
    const init: RequestInit = { method, headers, signal: controller.signal }
    if (options.body !== undefined) {
      headers['Content-Type'] = 'application/json'
      init.body = JSON.stringify(options.body)
    }

    const response = await fetch(buildUrl(path, options.query), init)
    const text = response.status === 204 ? '' : await response.text()
    if (!response.ok) {
      if (response.status === 401 && token && getAccessToken() === token) {
        clearAccessToken()
        for (const listener of unauthorizedListeners) listener()
      }
      throw toApiError(response, text)
    }
    return (text ? JSON.parse(text) : undefined) as T
  } catch (error) {
    if (error instanceof ApiError) throw error
    if (callerSignal?.aborted) throw error // cancelamento do chamador: não é falha de API
    if (timedOut) {
      throw new ApiError({ status: 0, code: 'TIMEOUT', message: 'The request timed out.', requestId })
    }
    throw new ApiError({
      status: 0,
      code: 'NETWORK_ERROR',
      message: 'Could not reach the API. Check that the backend is running and CORS is configured.',
      requestId,
    })
  } finally {
    clearTimeout(timer)
    callerSignal?.removeEventListener('abort', forwardAbort)
  }
}
