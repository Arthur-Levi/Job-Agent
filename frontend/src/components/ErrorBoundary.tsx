import { Component } from 'react'
import type { ErrorInfo, ReactNode } from 'react'
import { Button } from './Button'

interface Props {
  children: ReactNode
}

interface State {
  failed: boolean
}

/** Última linha de defesa: erro de renderização nunca deixa a tela em branco. */
export class ErrorBoundary extends Component<Props, State> {
  override state: State = { failed: false }

  static getDerivedStateFromError(): State {
    return { failed: true }
  }

  override componentDidCatch(error: Error, info: ErrorInfo): void {
    console.error('UI render error', error, info.componentStack)
  }

  override render(): ReactNode {
    if (!this.state.failed) return this.props.children
    return (
      <div role="alert" className="rounded-lg border border-rose-500/30 bg-rose-500/10 p-4">
        <h2 className="text-sm font-semibold text-rose-300">Something went wrong on this page</h2>
        <p className="mt-1 text-sm text-slate-300">Reload to try again. If it persists, check the console.</p>
        <Button variant="secondary" className="mt-3" onClick={() => window.location.reload()}>
          Reload
        </Button>
      </div>
    )
  }
}
