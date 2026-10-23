import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { applicationsApi } from '../services/applicationsApi'
import { ApiError } from '../services/http'
import { jobsApi } from '../services/jobsApi'
import { makeApplication, makeJob, pageOf } from '../test/fixtures'
import { JobDetailPage } from './JobDetailPage'

vi.mock('../services/jobsApi', () => ({
  jobsApi: { list: vi.fn(), get: vi.fn(), create: vi.fn(), update: vi.fn(), remove: vi.fn() },
}))
vi.mock('../services/applicationsApi', () => ({
  applicationsApi: { list: vi.fn(), create: vi.fn(), changeStatus: vi.fn(), get: vi.fn() },
}))

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/jobs/job-1']}>
      <Routes>
        <Route path="/jobs/:jobId" element={<JobDetailPage />} />
        <Route path="/jobs" element={<p>Jobs list</p>} />
      </Routes>
    </MemoryRouter>,
  )
}

beforeEach(() => {
  vi.resetAllMocks()
})

afterEach(() => {
  vi.restoreAllMocks()
})

describe('JobDetailPage', () => {
  it('shows the full description and facts', async () => {
    vi.mocked(jobsApi.get).mockResolvedValue(
      makeJob({ description: 'Line one\nLine two', location: 'Lisbon', salary_min: '5000.00', currency: 'BRL', work_model: 'REMOTE' }),
    )
    vi.mocked(applicationsApi.list).mockResolvedValue(pageOf([]))
    renderPage()

    expect(await screen.findByRole('heading', { name: 'Backend Developer' })).toBeInTheDocument()
    expect(screen.getByText(/Line one/)).toHaveTextContent('Line two')
    expect(screen.getByText('Remote', { selector: 'dd' })).toBeInTheDocument()
    expect(screen.getByText('Lisbon', { selector: 'dd' })).toBeInTheDocument()
  })

  it('renders the source as a safe external link', async () => {
    vi.mocked(jobsApi.get).mockResolvedValue(makeJob({ source: 'LinkedIn', source_url: 'https://jobs.example.com/1' }))
    vi.mocked(applicationsApi.list).mockResolvedValue(pageOf([]))
    renderPage()
    const link = await screen.findByRole('link', { name: 'LinkedIn' })
    expect(link).toHaveAttribute('href', 'https://jobs.example.com/1')
    expect(link).toHaveAttribute('rel', 'noopener noreferrer')
    expect(link).toHaveAttribute('target', '_blank')
  })

  it('never turns a non-http(s) source_url into a link', async () => {
    vi.mocked(jobsApi.get).mockResolvedValue(makeJob({ source: 'Imported', source_url: 'javascript:alert(1)' }))
    vi.mocked(applicationsApi.list).mockResolvedValue(pageOf([]))
    renderPage()
    await screen.findByText('Imported', { selector: 'dd' })
    expect(document.querySelector('a[href^="javascript"]')).toBeNull()
    expect(screen.queryByRole('link', { name: 'Imported' })).not.toBeInTheDocument()
  })

  it('shows an error when the job does not exist', async () => {
    vi.mocked(jobsApi.get).mockRejectedValue(new ApiError({ status: 404, code: 'JOB_NOT_FOUND', message: 'Job not found' }))
    vi.mocked(applicationsApi.list).mockResolvedValue(pageOf([]))
    renderPage()
    expect(await screen.findByRole('alert')).toHaveTextContent('Job not found')
    expect(screen.getByRole('link', { name: '← Back to jobs' })).toBeInTheDocument()
  })

  it('tracks the job as an application and then shows its status', async () => {
    vi.mocked(jobsApi.get).mockResolvedValue(makeJob())
    vi.mocked(applicationsApi.list).mockResolvedValueOnce(pageOf([]))
    vi.mocked(applicationsApi.create).mockResolvedValue({ ...makeApplication(), events: [] })
    vi.mocked(applicationsApi.list).mockResolvedValueOnce(pageOf([makeApplication({ status: 'DISCOVERED' })]))
    renderPage()

    fireEvent.click(await screen.findByRole('button', { name: 'Track application' }))

    await waitFor(() => expect(applicationsApi.create).toHaveBeenCalledWith('job-1'))
    expect(await screen.findByRole('link', { name: 'Open pipeline' })).toBeInTheDocument()
  })

  it('explains why a job with applications cannot be deleted (409)', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    vi.mocked(jobsApi.get).mockResolvedValue(makeJob())
    vi.mocked(applicationsApi.list).mockResolvedValue(pageOf([makeApplication()]))
    vi.mocked(jobsApi.remove).mockRejectedValue(
      new ApiError({ status: 409, code: 'JOB_HAS_APPLICATIONS', message: 'Job has applications and cannot be deleted' }),
    )
    renderPage()

    fireEvent.click(await screen.findByRole('button', { name: 'Delete' }))
    expect(await screen.findByText('Job has applications and cannot be deleted')).toBeInTheDocument()
    expect(screen.queryByText('Jobs list')).not.toBeInTheDocument()
  })

  it('goes back to the list after deleting', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    vi.mocked(jobsApi.get).mockResolvedValue(makeJob())
    vi.mocked(applicationsApi.list).mockResolvedValue(pageOf([]))
    vi.mocked(jobsApi.remove).mockResolvedValue(undefined)
    renderPage()

    fireEvent.click(await screen.findByRole('button', { name: 'Delete' }))
    expect(await screen.findByText('Jobs list')).toBeInTheDocument()
  })
})
