import { useState, type FormEvent } from 'react'
import { Link, Navigate } from 'react-router-dom'
import { useAuth } from '../app/authContext'
import { authApi } from '../services/authApi'
import { ApiError } from '../services/http'

export function RegisterPage() {
  const { status } = useAuth()
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [created, setCreated] = useState(false)
  if (status === 'authenticated') return <Navigate to="/dashboard" replace />

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (busy) return
    setError('')
    if (!name.trim() || name.trim().length > 200 || password.length < 12 || password.length > 128) {
      setError('Informe seu nome e uma senha de 12 a 128 caracteres.')
      return
    }
    setBusy(true)
    try {
      await authApi.register({ name: name.trim(), email: email.trim(), password })
      setPassword('')
      setCreated(true)
    } catch (cause) {
      setError(cause instanceof ApiError && cause.status === 429
        ? 'Muitas tentativas de cadastro. Aguarde alguns minutos antes de tentar novamente.'
        : cause instanceof ApiError && cause.status === 409
          ? 'Não foi possível cadastrar este email. Confira os dados ou tente entrar.'
          : 'Não foi possível cadastrar. Verifique os campos e tente novamente.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center p-5">
      <section className="w-full max-w-md rounded-xl border border-slate-800 bg-slate-900 p-7">
        <p className="mb-3 text-sm font-bold tracking-widest text-sky-400">JOB AGENT</p>
        <h1 className="mb-5 text-2xl font-semibold text-white">Criar conta</h1>
        {created ? (
          <div role="status" className="space-y-4">
            <p>Solicitação recebida. Se necessário, confirme seu email antes de entrar.</p>
            <Link to="/login" className="inline-block rounded-md bg-sky-600 px-4 py-3 text-white">Ir para login</Link>
          </div>
        ) : (
          <form onSubmit={submit} className="space-y-4">
            <div>
              <label htmlFor="register-name" className="mb-1 block text-sm">Nome</label>
              <input id="register-name" required maxLength={200} autoComplete="name" value={name} onChange={event => setName(event.target.value)} disabled={busy}
                className="w-full rounded-md border border-slate-700 bg-slate-950 p-3" />
            </div>
            <div>
              <label htmlFor="register-email" className="mb-1 block text-sm">Email</label>
              <input id="register-email" required type="email" autoComplete="email" value={email} onChange={event => setEmail(event.target.value)} disabled={busy}
                className="w-full rounded-md border border-slate-700 bg-slate-950 p-3" />
            </div>
            <div>
              <label htmlFor="register-password" className="mb-1 block text-sm">Senha (12 a 128 caracteres)</label>
              <input id="register-password" required type="password" minLength={12} maxLength={128} autoComplete="new-password" value={password} onChange={event => setPassword(event.target.value)} disabled={busy}
                className="w-full rounded-md border border-slate-700 bg-slate-950 p-3" />
            </div>
            {error && <p role="alert" className="text-sm text-rose-400">{error}</p>}
            <button disabled={busy} type="submit" className="w-full rounded-md bg-sky-600 p-3 font-semibold text-white disabled:opacity-50">
              {busy ? 'Criando…' : 'Criar conta'}
            </button>
          </form>
        )}
        <p className="mt-4 text-sm"><Link to="/request-verification" className="text-sky-400 underline">Solicitar confirmação de email</Link></p>
        <p className="mt-5 text-sm text-slate-400">Já tem conta? <Link to="/login" className="text-sky-400 underline">Entrar</Link></p>
      </section>
    </main>
  )
}
