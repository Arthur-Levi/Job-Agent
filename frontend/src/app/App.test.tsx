import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { applicationsApi } from '../services/applicationsApi'
import { jobsApi } from '../services/jobsApi'
import { pageOf } from '../test/fixtures'
import { App } from './App'

vi.mock('../services/jobsApi', () => ({ jobsApi: { list: vi.fn() } }))
vi.mock('../services/applicationsApi', () => ({ applicationsApi: { list: vi.fn() } }))
vi.mock('../services/profileApi', () => ({ profileApi: { get: vi.fn().mockResolvedValue(null) } }))

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>,
  )
}

beforeEach(() => {
  vi.mocked(jobsApi.list).mockResolvedValue(pageOf([]))
  vi.mocked(applicationsApi.list).mockResolvedValue(pageOf([]))
})

describe('routing and shell', () => {
  it('redirects / to the dashboard and renders the shell navigation', async () => {
    renderAt('/')
    expect(await screen.findByRole('heading', { name: 'JOB COMMAND' })).toBeInTheDocument()
    const nav = screen.getByRole('navigation', { name: 'Main' })
    for (const label of ['Dashboard', 'Profile', 'Jobs', 'Applications']) {
      expect(nav).toHaveTextContent(label)
    }
    expect(screen.getByText('JOB AGENT')).toBeInTheDocument()
  })

  it.each([
    ['/profile', 'Profile'],
    ['/jobs', 'Jobs'],
    ['/applications', 'Applications'],
  ])('renders %s', async (path, heading) => {
    renderAt(path)
    expect(await screen.findByRole('heading', { level: 1, name: heading })).toBeInTheDocument()
  })

  it('renders the 404 page for unknown routes', () => {
    renderAt('/nope/nothing')
    expect(screen.getByText('Page not found')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Back to dashboard' })).toHaveAttribute('href', '/dashboard')
  })
})
