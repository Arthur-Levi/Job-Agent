import { useCallback, useEffect, useState } from 'react'
import { isAbortError } from '../services/http'

export type Fetcher<T> = (signal: AbortSignal) => Promise<T>

export type QueryState<T> =
  | { status: 'loading' }
  | { status: 'error'; error: unknown }
  | { status: 'success'; data: T }

export interface QueryResult<T> {
  state: QueryState<T>
  /** true enquanto recarrega (reload) mostrando os dados anteriores. */
  refreshing: boolean
  reload: () => void
}

interface Settled<T> {
  fetcher: Fetcher<T>
  nonce: number
  outcome: Exclude<QueryState<T>, { status: 'loading' }>
}

/**
 * Carrega dados e expõe loading | error | success. Regras:
 * - `fetcher` deve ser estável (useCallback): trocar o fetcher dispara nova busca;
 * - respostas de buscas antigas/canceladas são descartadas (AbortController);
 * - `reload()` mantém o resultado anterior visível (refreshing=true) até chegar o novo.
 */
export function useApiQuery<T>(fetcher: Fetcher<T>): QueryResult<T> {
  const [nonce, setNonce] = useState(0)
  const [settled, setSettled] = useState<Settled<T> | null>(null)

  useEffect(() => {
    const controller = new AbortController()
    fetcher(controller.signal).then(
      (data) => {
        if (!controller.signal.aborted) {
          setSettled({ fetcher, nonce, outcome: { status: 'success', data } })
        }
      },
      (error: unknown) => {
        if (controller.signal.aborted || isAbortError(error)) return
        setSettled({ fetcher, nonce, outcome: { status: 'error', error } })
      },
    )
    return () => controller.abort()
  }, [fetcher, nonce])

  const reload = useCallback(() => setNonce((n) => n + 1), [])

  if (settled && settled.fetcher === fetcher) {
    if (settled.nonce === nonce) return { state: settled.outcome, refreshing: false, reload }
    if (settled.outcome.status === 'success') {
      return { state: settled.outcome, refreshing: true, reload }
    }
  }
  return { state: { status: 'loading' }, refreshing: false, reload }
}
