import { useEffect, useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { authApi } from '../services/authApi'
import { ApiError } from '../services/http'

function secretFromFragment(): string {
  const raw = new URLSearchParams(window.location.hash.replace(/^#/, '')).get('token') ?? ''
  return /^[A-Za-z0-9_-]{32,256}$/.test(raw) ? raw : ''
}

function ClearFragment() {
  useEffect(() => {
    if (window.location.hash.includes('token=')) {
      window.history.replaceState(window.history.state, '', window.location.pathname)
    }
  }, [])
  return null
}

export function RequestAccountEmailPage({ purpose }: { purpose: 'verify' | 'reset' }) {
  const [email, setEmail] = useState('')
  const [sent, setSent] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const reset = purpose === 'reset'
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (busy) return
    setBusy(true)
    setError('')
    try {
      if (reset) await authApi.requestPasswordReset(email.trim())
      else await authApi.requestVerification(email.trim())
      setSent(true)
    } catch (cause) {
      setError(cause instanceof ApiError && cause.status === 429
        ? 'Muitas tentativas. Aguarde e tente novamente.'
        : 'Não foi possível processar agora. Tente novamente.')
    } finally {
      setBusy(false)
    }
  }
  return (
    <main className="mx-auto min-h-screen max-w-md p-8">
      <h1 className="mb-5 text-2xl font-semibold">{reset ? 'Recuperar senha' : 'Confirmar email'}</h1>
      {sent ? <p role="status">Se existir uma conta elegível, enviaremos instruções para seu email.</p>
        : <form onSubmit={submit} className="space-y-4">
          <label htmlFor="recovery-email" className="block">Email</label>
          <input id="recovery-email" type="email" required autoComplete="email"
            value={email} onChange={event => setEmail(event.target.value)}
            className="w-full rounded border p-3 text-slate-900" />
          {error && <p role="alert">{error}</p>}
          <button type="submit" disabled={busy} className="rounded bg-sky-600 p-3 text-white">
            {busy ? 'Enviando…' : 'Enviar instruções'}
          </button>
        </form>}
      <p className="mt-5"><Link to="/login">Voltar ao login</Link></p>
    </main>
  )
}

export function VerifyEmailPage() {
  const [token] = useState(secretFromFragment)
  const [status, setStatus] = useState('')
  const [busy, setBusy] = useState(false)
  async function submit() {
    if (!token || busy) return
    setBusy(true)
    try {
      await authApi.verifyEmail(token)
      setStatus('Email confirmado. Você já pode entrar.')
    } catch {
      setStatus('Link inválido ou expirado. Solicite outro email de confirmação.')
    } finally {
      setBusy(false)
    }
  }
  return <main className="mx-auto min-h-screen max-w-md p-8">
    <ClearFragment />
    <h1 className="mb-5 text-2xl font-semibold">Confirmar email</h1>
    {status ? <p role="status">{status}</p> : token
      ? <button disabled={busy} onClick={submit} className="rounded bg-sky-600 p-3 text-white">
        Confirmar meu email
      </button> : <p role="alert">Link de confirmação ausente ou inválido.</p>}
    <p className="mt-5"><Link to="/request-verification">Solicitar novo link</Link></p>
    <p><Link to="/login">Ir para login</Link></p>
  </main>
}

export function ResetPasswordPage() {
  const [token] = useState(secretFromFragment)
  const [password, setPassword] = useState('')
  const [status, setStatus] = useState('')
  const [busy, setBusy] = useState(false)
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!token || busy || password.length < 12 || password.length > 128) return
    setBusy(true)
    try {
      await authApi.resetPassword(token, password)
      setPassword('')
      setStatus('Senha atualizada. Todas as sessões anteriores foram encerradas.')
    } catch {
      setStatus('Link inválido ou expirado. Solicite outra redefinição.')
    } finally {
      setBusy(false)
    }
  }
  return <main className="mx-auto min-h-screen max-w-md p-8">
    <ClearFragment />
    <h1 className="mb-5 text-2xl font-semibold">Redefinir senha</h1>
    {status ? <p role="status">{status}</p> : token
      ? <form onSubmit={submit} className="space-y-4">
        <label htmlFor="new-password">Nova senha (12 a 128 caracteres)</label>
        <input id="new-password" type="password" autoComplete="new-password"
          required minLength={12} maxLength={128} value={password}
          onChange={event => setPassword(event.target.value)}
          className="w-full rounded border p-3 text-slate-900" />
        <button disabled={busy} type="submit" className="rounded bg-sky-600 p-3 text-white">
          Atualizar senha
        </button>
      </form> : <p role="alert">Link de recuperação ausente ou inválido.</p>}
    <p className="mt-5"><Link to="/request-password-reset">Solicitar novo link</Link></p>
    <p><Link to="/login">Ir para login</Link></p>
  </main>
}
