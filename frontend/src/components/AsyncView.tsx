import type { ReactNode } from 'react'
import type { QueryResult } from '../hooks/useApiQuery'
import { ErrorState, LoadingState } from './States'

interface AsyncViewProps<T> {
  query: QueryResult<T>
  /** Quando devolve true, renderiza `empty` em vez de `children`. */
  isEmpty?: (data: T) => boolean
  empty?: ReactNode
  loadingLabel?: string
  children: (data: T) => ReactNode
}

/** Os quatro estados de uma tela que consome a API: loading, error, empty e success. */
export function AsyncView<T>({ query, isEmpty, empty, loadingLabel, children }: AsyncViewProps<T>) {
  const { state, refreshing, reload } = query
  if (state.status === 'loading') return <LoadingState label={loadingLabel} />
  if (state.status === 'error') return <ErrorState error={state.error} onRetry={reload} />
  if (isEmpty?.(state.data)) return <>{empty}</>
  return (
    <div aria-busy={refreshing} className={refreshing ? 'opacity-60 transition-opacity' : ''}>
      {children(state.data)}
    </div>
  )
}
