import { ApiError } from '../services/http'

export interface ErrorDescription {
  title: string
  message: string
  requestId: string | null
}

export function describeError(error: unknown): ErrorDescription {
  if (error instanceof ApiError) {
    const title =
      error.status === 0
        ? 'Connection problem'
        : error.status >= 500
          ? 'Server error'
          : 'Request failed'
    return { title, message: error.message, requestId: error.requestId }
  }
  const message = error instanceof Error ? error.message : 'Something went wrong.'
  return { title: 'Unexpected error', message, requestId: null }
}

interface ValidationDetail {
  loc?: unknown[]
  message?: string
}

/** 422 VALIDATION_ERROR -> { campo: mensagem } (loc = ["body", "campo", ...]). */
export function fieldErrorsFrom(error: unknown): Record<string, string> {
  if (!(error instanceof ApiError) || error.code !== 'VALIDATION_ERROR') return {}
  if (!Array.isArray(error.details)) return {}
  const result: Record<string, string> = {}
  for (const detail of error.details as ValidationDetail[]) {
    const field = detail.loc?.[1]
    if (typeof field === 'string' && detail.message && !(field in result)) {
      result[field] = detail.message
    }
  }
  return result
}
