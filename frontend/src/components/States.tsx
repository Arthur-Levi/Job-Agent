import type { ReactNode } from 'react'
import { describeError } from '../utils/errors'
import { Button } from './Button'

export function LoadingState({ label = 'Loading…' }: { label?: string }) {
  return (
    <div role="status" className="flex items-center gap-3 py-10 text-sm text-slate-400">
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-slate-600 border-t-sky-400" />
      {label}
    </div>
  )
}

interface ErrorStateProps {
  error: unknown
  onRetry?: () => void
}

export function ErrorState({ error, onRetry }: ErrorStateProps) {
  const { title, message, requestId } = describeError(error)
  return (
    <div role="alert" className="rounded-lg border border-rose-500/30 bg-rose-500/10 p-4">
      <h2 className="text-sm font-semibold text-rose-300">{title}</h2>
      <p className="mt-1 text-sm text-slate-300">{message}</p>
      {requestId ? <p className="mt-2 text-xs text-slate-500">Request ID: {requestId}</p> : null}
      {onRetry ? (
        <Button variant="secondary" className="mt-3" onClick={onRetry}>
          Try again
        </Button>
      ) : null}
    </div>
  )
}

/** Erro inline (ação/formulário), mais discreto que ErrorState. */
export function ErrorBanner({ error }: { error: unknown }) {
  const { message, requestId } = describeError(error)
  return (
    <p role="alert" className="rounded-md border border-rose-500/30 bg-rose-500/10 px-3 py-2 text-sm text-rose-300">
      {message}
      {requestId ? <span className="ml-2 text-xs text-slate-500">({requestId})</span> : null}
    </p>
  )
}

interface EmptyStateProps {
  title: string
  description?: string
  action?: ReactNode
}

export function EmptyState({ title, description, action }: EmptyStateProps) {
  return (
    <div className="rounded-lg border border-dashed border-slate-700 px-4 py-10 text-center">
      <h2 className="text-sm font-semibold text-slate-200">{title}</h2>
      {description ? <p className="mx-auto mt-1 max-w-md text-sm text-slate-400">{description}</p> : null}
      {action ? <div className="mt-4 flex justify-center">{action}</div> : null}
    </div>
  )
}
