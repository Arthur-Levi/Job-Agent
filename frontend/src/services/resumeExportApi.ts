import { clearAccessToken, getAccessToken } from './authSession'
import { ApiError, getBaseUrl, newRequestId } from './http'

export type ExportFormat = 'pdf' | 'docx'

/** A binary response cannot use the JSON-only http.request helper. */
export async function downloadApprovedResume(
  format: ExportFormat,
  digest: string,
  signal?: AbortSignal,
): Promise<Blob> {
  const token = getAccessToken()
  if (!token) {
    throw new ApiError({ status: 401, code: 'UNAUTHORIZED', message: 'Faça login novamente.' })
  }
  const controller = new AbortController()
  const onAbort = () => controller.abort()
  if (signal?.aborted) controller.abort()
  signal?.addEventListener('abort', onAbort)
  const timeout = setTimeout(() => controller.abort(), 20_000)
  try {
    const response = await fetch(`${getBaseUrl()}/api/v1/career/resume-export/${format}`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
        Accept: format === 'pdf' ? 'application/pdf' : 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'X-Request-ID': newRequestId(),
      },
      body: JSON.stringify({ approved: true, approval_sha256: digest }),
      signal: controller.signal,
    })
    if (!response.ok) {
      if (response.status === 401 && getAccessToken() === token) clearAccessToken()
      const envelope: unknown = await response.json().catch(() => null)
      const error = envelope && typeof envelope === 'object' && 'error' in envelope
        ? envelope.error : null
      const payload = error && typeof error === 'object' ? error as Record<string, unknown> : {}
      throw new ApiError({
        status: response.status,
        code: typeof payload.code === 'string' ? payload.code : `HTTP_${response.status}`,
        message: typeof payload.message === 'string' ? payload.message : 'Não foi possível exportar.',
      })
    }
    const expected = format === 'pdf' ? 'application/pdf' : 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    if (!(response.headers.get('content-type') ?? '').toLowerCase().includes(expected)) {
      throw new ApiError({ status: 0, code: 'INVALID_EXPORT', message: 'Formato inesperado na resposta.' })
    }
    const bytes = await response.blob()
    if (bytes.size === 0 || bytes.size > 500_000) {
      throw new ApiError({ status: 0, code: 'INVALID_EXPORT', message: 'O documento retornado é inválido.' })
    }
    return bytes
  } catch (error) {
    if (error instanceof ApiError) throw error
    if (signal?.aborted) throw error
    throw new ApiError({ status: 0, code: 'NETWORK_ERROR', message: 'Não foi possível concluir o download.' })
  } finally {
    clearTimeout(timeout)
    signal?.removeEventListener('abort', onAbort)
  }
}
