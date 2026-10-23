import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { applicationsApi } from '../services/applicationsApi'
import { ApiError } from '../services/http'
import { jobsApi } from '../services/jobsApi'
import { pageOf } from '../test/fixtures'
import type { ApplicationStatus } from '../types/api'
import { DashboardPage } from './DashboardPage'

vi.mock('../services/jobsApi', () => ({ jobsApi: { list: vi.fn() } }))
vi.mock('../services/applicationsApi', () => ({ applicationsApi: { list: vi.fn() } }))

function totals(map: { jobs: number; all: number; byStatus: Partial<Record<ApplicationStatus, number>> }) {
  vi.mocked(jobsApi.list).mockResolvedValue(pageOf([], map.jobs))
  vi.mocked(applicationsApi.list).mockImplementation((params) =>
    Promise.resolve(pageOf([], params?.status ? (map.byStatus[params.status] ?? 0) : map.all)),
  )
}

function renderPage() {
  return render(
    <MemoryRouter>
      <DashboardPage />
    </MemoryRouter>,
  )
}

function metric(label: string) {
  return screen.getByText(label).parentElement
}

beforeEach(() => {
  vi.resetAllMocks()
})

describe('DashboardPage', () => {
  it('shows only real counts (interviews = INTERVIEW + TECHNICAL)', async () => {
    totals({ jobs: 12, all: 3, byStatus: { READY: 1, INTERVIEW: 0, TECHNICAL: 1 } })
    renderPage()

    await screen.findByText('Jobs')
    expect(metric('Jobs')).toHaveTextContent('12')
    expect(metric('Applications')).toHaveTextContent('3')
    expect(metric('Ready')).toHaveTextContent('1')
    expect(metric('Interviews')).toHaveTextContent('1')
    expect(screen.queryByText(/Add your first job/)).not.toBeInTheDocument()
  })

  it('shows zeros (not fake data) and a hint when the database is empty', async () => {
    totals({ jobs: 0, all: 0, byStatus: {} })
    renderPage()

    await screen.findByText('Jobs')
    for (const label of ['Jobs', 'Applications', 'Ready', 'Interviews']) {
      expect(metric(label)).toHaveTextContent('0')
    }
    expect(screen.getByText(/Add your first job/)).toBeInTheDocument()
  })

  it('links the Ready card to the filtered pipeline', async () => {
    totals({ jobs: 1, all: 1, byStatus: { READY: 1 } })
    renderPage()
    const card = (await screen.findByText('Ready')).closest('a')
    expect(card).toHaveAttribute('href', '/applications?status=READY')
  })

  it('shows an error state when any request fails', async () => {
    vi.mocked(jobsApi.list).mockRejectedValue(new ApiError({ status: 0, code: 'NETWORK_ERROR', message: 'down' }))
    vi.mocked(applicationsApi.list).mockResolvedValue(pageOf([]))
    renderPage()
    expect(await screen.findByRole('alert')).toHaveTextContent('down')
  })
})
