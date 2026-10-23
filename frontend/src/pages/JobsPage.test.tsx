import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError } from '../services/http'
import { jobsApi } from '../services/jobsApi'
import { makeJob, pageOf } from '../test/fixtures'
import { JobsPage } from './JobsPage'

vi.mock('../services/jobsApi', () => ({
  jobsApi: { list: vi.fn(), get: vi.fn(), create: vi.fn(), update: vi.fn(), remove: vi.fn() },
}))

const list = vi.mocked(jobsApi.list)
const create = vi.mocked(jobsApi.create)

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/jobs']}>
      <JobsPage />
    </MemoryRouter>,
  )
}

beforeEach(() => {
  vi.resetAllMocks()
})

describe('JobsPage states', () => {
  it('shows loading, then the jobs', async () => {
    list.mockResolvedValue(pageOf([makeJob({ title: 'Python Developer', company: 'XYZ', status: 'OPEN' })]))
    renderPage()

    expect(screen.getByRole('status')).toHaveTextContent('Loading jobs')
    const link = await screen.findByRole('link', { name: 'Python Developer' })
    expect(link).toHaveAttribute('href', '/jobs/job-1')
    expect(screen.getByText('XYZ')).toBeInTheDocument()
    expect(screen.getByText('Open', { selector: 'span' })).toBeInTheDocument()
  })

  it('shows the empty state when there are no jobs', async () => {
    list.mockResolvedValue(pageOf([]))
    renderPage()
    expect(await screen.findByText('No jobs yet')).toBeInTheDocument()
  })

  it('shows the error with request id and recovers on retry', async () => {
    list.mockRejectedValueOnce(
      new ApiError({ status: 500, code: 'INTERNAL_ERROR', message: 'Internal server error', requestId: 'req-abcdef12' }),
    )
    list.mockResolvedValueOnce(pageOf([makeJob({ title: 'Recovered job' })]))
    renderPage()

    const alert = await screen.findByRole('alert')
    expect(alert).toHaveTextContent('Internal server error')
    expect(alert).toHaveTextContent('req-abcdef12')

    fireEvent.click(screen.getByRole('button', { name: 'Try again' }))
    expect(await screen.findByText('Recovered job')).toBeInTheDocument()
  })

  it('shows a connection error instead of a blank page when the API is down', async () => {
    list.mockRejectedValue(new ApiError({ status: 0, code: 'NETWORK_ERROR', message: 'Could not reach the API.' }))
    renderPage()
    expect(await screen.findByText('Connection problem')).toBeInTheDocument()
  })

  it('refetches from the first page when the status filter changes', async () => {
    list.mockResolvedValue(pageOf([makeJob()]))
    renderPage()
    await screen.findByText('Backend Developer')

    fireEvent.change(screen.getByLabelText('Status'), { target: { value: 'CLOSED' } })

    await waitFor(() => expect(list).toHaveBeenLastCalledWith({ limit: 20, offset: 0, status: 'CLOSED' }, expect.anything()))
  })

  it('explains an empty filtered result differently', async () => {
    list.mockResolvedValueOnce(pageOf([makeJob()]))
    list.mockResolvedValueOnce(pageOf([]))
    renderPage()
    await screen.findByText('Backend Developer')
    fireEvent.change(screen.getByLabelText('Status'), { target: { value: 'ARCHIVED' } })
    expect(await screen.findByText('No jobs match this filter')).toBeInTheDocument()
  })
})

describe('Add Job form', () => {
  async function openForm() {
    list.mockResolvedValue(pageOf([makeJob()]))
    renderPage()
    await screen.findByText('Backend Developer')
    fireEvent.click(screen.getByRole('button', { name: 'Add Job' }))
  }

  it('blocks submit and shows field errors for missing required fields', async () => {
    await openForm()
    fireEvent.click(screen.getByRole('button', { name: 'Add job' }))

    expect(await screen.findByText('Title is required')).toBeInTheDocument()
    expect(screen.getByText('Company is required')).toBeInTheDocument()
    expect(screen.getByText('Description is required')).toBeInTheDocument()
    expect(create).not.toHaveBeenCalled()
  })

  it('submits a normalized payload', async () => {
    create.mockResolvedValue(makeJob({ id: 'new-1' }))
    await openForm()

    fireEvent.change(screen.getByLabelText('Title *'), { target: { value: ' Data Engineer ' } })
    fireEvent.change(screen.getByLabelText('Company *'), { target: { value: 'Globex' } })
    fireEvent.change(screen.getByLabelText('Description *'), { target: { value: 'Pipelines' } })
    fireEvent.change(screen.getByLabelText('Salary min'), { target: { value: '5000' } })
    fireEvent.change(screen.getByLabelText('Currency'), { target: { value: 'brl' } })
    fireEvent.click(screen.getByRole('button', { name: 'Add job' }))

    await waitFor(() => expect(create).toHaveBeenCalledTimes(1))
    expect(create.mock.calls[0]?.[0]).toMatchObject({
      title: 'Data Engineer',
      company: 'Globex',
      salary_min: '5000',
      salary_max: null,
      currency: 'BRL',
      location: null,
      status: 'OPEN',
    })
  })

  it('shows server-side field errors (422) next to the fields', async () => {
    create.mockRejectedValue(
      new ApiError({
        status: 422,
        code: 'VALIDATION_ERROR',
        message: 'Request validation failed',
        details: [{ loc: ['body', 'source_url'], message: 'Input should be a valid URL', type: 'url_parsing' }],
      }),
    )
    await openForm()
    fireEvent.change(screen.getByLabelText('Title *'), { target: { value: 'T' } })
    fireEvent.change(screen.getByLabelText('Company *'), { target: { value: 'C' } })
    fireEvent.change(screen.getByLabelText('Description *'), { target: { value: 'D' } })
    fireEvent.change(screen.getByLabelText('Source URL'), { target: { value: 'ftp://nope' } })
    fireEvent.click(screen.getByRole('button', { name: 'Add job' }))

    expect(await screen.findByText('Input should be a valid URL')).toBeInTheDocument()
  })

  it('shows a banner for non-field errors such as a duplicate URL (409)', async () => {
    create.mockRejectedValue(
      new ApiError({ status: 409, code: 'JOB_SOURCE_URL_EXISTS', message: 'A job with this source_url already exists' }),
    )
    await openForm()
    fireEvent.change(screen.getByLabelText('Title *'), { target: { value: 'T' } })
    fireEvent.change(screen.getByLabelText('Company *'), { target: { value: 'C' } })
    fireEvent.change(screen.getByLabelText('Description *'), { target: { value: 'D' } })
    fireEvent.click(screen.getByRole('button', { name: 'Add job' }))

    expect(await screen.findByText(/already exists/)).toBeInTheDocument()
  })
})
