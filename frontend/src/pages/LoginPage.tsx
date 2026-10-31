import { useState, type FormEvent } from 'react'
import { Link, Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '../app/authContext'
import { ApiError } from '../services/http'

export function LoginPage() {
  const { status, login } = useAuth()
  const location = useLocation()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const destination = (location.state as { from?: string } | null)?.from
  const redirect = destination?.startsWith('/') && !destination.startsWith('//') && !destination.startsWith('/login') && !destination.startsWith('/register')
    ? destination : '/dashboard'

  if (status === 'authenticated') return <Navigate to={redirect} replace />

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (busy) return
    setError('')
    setBusy(true)
    try {
      await login({ email: email.trim(), password })
    } catch (cause) {
      setError(cause instanceof ApiError && cause.status === 429
        ? 'Muitas tentativas de acesso. Aguarde alguns minutos antes de tentar novamente.'
        : cause instanceof ApiError && cause.status === 401
          ? 'Email ou senha inválidos.'
          : 'Não foi possível entrar. Tente novamente.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center p-5">
      <section className="w-full max-w-md rounded-xl border border-slate-800 bg-slate-900 p-7 shadow-xl">
        <p className="mb-3 text-sm font-bold tracking-widest text-sky-400">JOB AGENT</p>
        <h1 className="mb-2 text-2xl font-semibold text-white">Entrar na sua conta</h1>
        <p className="mb-6 text-sm text-slate-400">Acesse suas vagas e candidaturas.</p>
        <form onSubmit={submit} className="space-y-4">
          <div>
            <label className="mb-1 block text-sm" htmlFor="login-email">Email</label>
            <input id="login-email" type="email" required autoComplete="email" value={email} onChange={event => setEmail(event.target.value)} disabled={busy}
              className="w-full rounded-md border border-slate-700 bg-slate-950 p-3" />
          </div>
          <div>
            <label className="mb-1 block text-sm" htmlFor="login-password">Senha</label>
            <input id="login-password" type="password" required autoComplete="current-password" value={password} onChange={event => setPassword(event.target.value)} disabled={busy}
              className="w-full rounded-md border border-slate-700 bg-slate-950 p-3" />
          </div>
          {error && <p role="alert" className="text-sm text-rose-400">{error}</p>}
          <button type="submit" disabled={busy} className="w-full rounded-md bg-sky-600 p-3 font-semibold text-white disabled:opacity-50">
            {busy ? 'Entrando…' : 'Entrar'}
          </button>
        </form>
        <p className="mt-4 text-sm"><Link to="/request-password-reset" className="text-sky-400 underline">Esqueci minha senha</Link></p>
        <p className="mt-4 text-sm"><Link to="/request-verification" className="text-sky-400 underline">Reenviar confirmação de email</Link></p>
        <p className="mt-5 text-sm text-slate-400">Não tem conta? <Link to="/register" className="text-sky-400 underline">Cadastre-se</Link></p>
      </section>
    </main>
  )
}
