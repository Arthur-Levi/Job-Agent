import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { applicationsApi } from '../services/applicationsApi'
import { authApi } from '../services/authApi'
import { clearAccessToken, setAccessToken } from '../services/authSession'
import { jobsApi } from '../services/jobsApi'
import { pageOf } from '../test/fixtures'
import { App } from './App'

vi.mock('../services/jobsApi', () => ({ jobsApi: { list: vi.fn() } }))
vi.mock('../services/applicationsApi', () => ({ applicationsApi: { list: vi.fn() } }))
vi.mock('../services/profileApi', () => ({ profileApi: { get: vi.fn().mockResolvedValue(null) } }))
vi.mock('../services/authApi', () => ({
  authApi: { hasSession: vi.fn(), me: vi.fn(), login: vi.fn(), register: vi.fn(), logout: vi.fn() },
}))

const user = { id: 'synthetic-1', name: 'Test Candidate', email: 'test@example.com' }
function renderAt(path: string) {
  return render(<MemoryRouter initialEntries={[path]}><App /></MemoryRouter>)
}

beforeEach(() => {
  vi.clearAllMocks()
  clearAccessToken()
  setAccessToken('t'.repeat(64))
  vi.mocked(jobsApi.list).mockResolvedValue(pageOf([]))
  vi.mocked(applicationsApi.list).mockResolvedValue(pageOf([]))
  vi.mocked(authApi.hasSession).mockReturnValue(true)
  vi.mocked(authApi.me).mockResolvedValue(user)
  vi.mocked(authApi.login).mockResolvedValue(user)
  vi.mocked(authApi.register).mockResolvedValue(user)
  vi.mocked(authApi.logout).mockResolvedValue(undefined)
})

describe('authenticated routing and shell', () => {
  it('redirects / to the dashboard and renders the shell navigation', async () => {
    renderAt('/')
    expect(await screen.findByRole('heading', { name: 'JOB COMMAND' })).toBeInTheDocument()
    const nav = screen.getByRole('navigation', { name: 'Main' })
    for (const label of ['Dashboard', 'Profile', 'Jobs', 'Applications']) {
      expect(nav).toHaveTextContent(label)
    }
    expect(screen.getByText('JOB AGENT')).toBeInTheDocument()
    expect(screen.getByText(/Test Candidate/)).toBeInTheDocument()
  })

  it.each([
    ['/profile', 'Profile'],
    ['/jobs', 'Jobs'],
    ['/applications', 'Applications'],
  ])('renders %s after identity verification', async (path, heading) => {
    renderAt(path)
    expect(await screen.findByRole('heading', { level: 1, name: heading })).toBeInTheDocument()
  })

  it('renders 404 only for an authenticated user', async () => {
    renderAt('/nope/nothing')
    expect(await screen.findByText('Page not found')).toBeInTheDocument()
  })

  it('redirects unauthenticated private routes to login', async () => {
    clearAccessToken()
    vi.mocked(authApi.hasSession).mockReturnValue(false)
    renderAt('/jobs')
    expect(await screen.findByRole('heading', { name: 'Entrar na sua conta' })).toBeInTheDocument()
    expect(jobsApi.list).not.toHaveBeenCalled()
  })

  it('never renders private content when /me rejects the session', async () => {
    vi.mocked(authApi.me).mockRejectedValue(new Error('expired'))
    renderAt('/dashboard')
    expect(await screen.findByRole('heading', { name: 'Entrar na sua conta' })).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'JOB COMMAND' })).not.toBeInTheDocument()
  })

  it('logs in and returns to the requested private route', async () => {
    clearAccessToken()
    vi.mocked(authApi.hasSession).mockReturnValue(false)
    renderAt('/jobs')
    fireEvent.change(await screen.findByLabelText('Email'), { target: { value: 'test@example.com' } })
    fireEvent.change(screen.getByLabelText('Senha'), { target: { value: 'synthetic-password-123' } })
    fireEvent.click(screen.getByRole('button', { name: 'Entrar' }))
    expect(await screen.findByRole('heading', { name: 'Jobs' })).toBeInTheDocument()
    expect(authApi.login).toHaveBeenCalledWith({ email: 'test@example.com', password: 'synthetic-password-123' })
  })

  it('logs out and hides private data', async () => {
    renderAt('/dashboard')
    fireEvent.click(await screen.findByRole('button', { name: 'Sair' }))
    expect(await screen.findByRole('heading', { name: 'Entrar na sua conta' })).toBeInTheDocument()
    await waitFor(() => expect(authApi.logout).toHaveBeenCalledOnce())
    expect(screen.queryByText(/Test Candidate/)).not.toBeInTheDocument()
  })

  it('registers but requires login before displaying private pages', async () => {
    clearAccessToken()
    vi.mocked(authApi.hasSession).mockReturnValue(false)
    renderAt('/register')
    fireEvent.change(await screen.findByLabelText('Nome'), { target: { value: 'Synthetic Candidate' } })
    fireEvent.change(screen.getByLabelText('Email'), { target: { value: 'candidate@example.com' } })
    fireEvent.change(screen.getByLabelText('Senha (12 a 128 caracteres)'), { target: { value: 'synthetic-pass-1234' } })
    fireEvent.click(screen.getByRole('button', { name: 'Criar conta' }))
    expect(await screen.findByText(/Cadastro realizado/)).toBeInTheDocument()
    expect(authApi.register).toHaveBeenCalledOnce()
    expect(screen.queryByRole('heading', { name: 'JOB COMMAND' })).not.toBeInTheDocument()
  })
})
