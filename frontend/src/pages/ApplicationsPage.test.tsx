import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { applicationsApi } from '../services/applicationsApi'
import { ApiError } from '../services/http'
import { makeApplication, pageOf } from '../test/fixtures'
import { ApplicationsPage } from './ApplicationsPage'

vi.mock('../services/applicationsApi', () => ({
  applicationsApi: { list: vi.fn(), get: vi.fn(), create: vi.fn(), changeStatus: vi.fn() },
}))

const list = vi.mocked(applicationsApi.list)
const changeStatus = vi.mocked(applicationsApi.changeStatus)

function renderPage(url = '/applications') {
  return render(
    <MemoryRouter initialEntries={[url]}>
      <ApplicationsPage />
    </MemoryRouter>,
  )
}

beforeEach(() => {
  vi.resetAllMocks()
})

afterEach(() => {
  vi.restoreAllMocks()
})

describe('ApplicationsPage', () => {
  it('lists job, company and status', async () => {
    list.mockResolvedValue(pageOf([makeApplication({ status: 'APPLIED', allowed_next_statuses: ['RESPONSE'] })]))
    renderPage()

    expect(await screen.findByRole('link', { name: 'Backend Developer' })).toHaveAttribute('href', '/jobs/job-1')
    expect(screen.getByText('ACME')).toBeInTheDocument()
    expect(screen.getAllByText('Applied').length).toBeGreaterThan(0)
  })

  it('shows the empty state with a way forward', async () => {
    list.mockResolvedValue(pageOf([]))
    renderPage()
    expect(await screen.findByText('No applications yet')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Go to jobs' })).toHaveAttribute('href', '/jobs')
  })

  it('shows the error state and retries', async () => {
    list.mockRejectedValueOnce(new ApiError({ status: 503, code: 'DATABASE_UNAVAILABLE', message: 'Database is not reachable' }))
    list.mockResolvedValueOnce(pageOf([makeApplication()]))
    renderPage()
    expect(await screen.findByRole('alert')).toHaveTextContent('Database is not reachable')
    fireEvent.click(screen.getByRole('button', { name: 'Try again' }))
    expect(await screen.findByRole('link', { name: 'Backend Developer' })).toBeInTheDocument()
  })

  it('reads the status filter from the URL (dashboard link-through)', async () => {
    list.mockResolvedValue(pageOf([makeApplication({ status: 'READY' })]))
    renderPage('/applications?status=READY')
    await screen.findByRole('link', { name: 'Backend Developer' })
    expect(list).toHaveBeenCalledWith({ limit: 20, offset: 0, status: 'READY' }, expect.anything())
    expect(screen.getByLabelText('Status')).toHaveValue('READY')
  })

  it('ignores an invalid status in the URL', async () => {
    list.mockResolvedValue(pageOf([makeApplication()]))
    renderPage('/applications?status=BOGUS')
    await screen.findByRole('link', { name: 'Backend Developer' })
    expect(list).toHaveBeenCalledWith({ limit: 20, offset: 0 }, expect.anything())
  })
})

describe('StatusChanger', () => {
  async function renderWithOne() {
    list.mockResolvedValue(pageOf([makeApplication()]))
    changeStatus.mockResolvedValue({ ...makeApplication({ status: 'QUALIFIED' }), events: [] })
    renderPage()
    return screen.findByLabelText('Change status of Backend Developer')
  }

  it('offers the backend-provided next statuses, and the rest as forced corrections', async () => {
    const select = await renderWithOne()
    const next = within(within(select).getByRole('group', { name: 'Next' }))
    expect(next.getAllByRole('option').map((o) => o.textContent)).toEqual(['Qualified', 'Withdrawn'])
    const forced = within(within(select).getByRole('group', { name: 'Correct (forced)' }))
    expect(forced.getAllByRole('option').map((o) => o.textContent)).toContain('Offer')
    expect(forced.queryByRole('option', { name: 'Qualified' })).not.toBeInTheDocument()
  })

  it('applies a normal transition without force and reloads the list', async () => {
    const select = await renderWithOne()
    fireEvent.change(select, { target: { value: 'QUALIFIED' } })

    await waitFor(() => expect(changeStatus).toHaveBeenCalledWith('app-1', { status: 'QUALIFIED' }))
    await waitFor(() => expect(list).toHaveBeenCalledTimes(2))
  })

  it('asks for confirmation before a forced change and sends force: true', async () => {
    const confirm = vi.spyOn(window, 'confirm').mockReturnValue(true)
    const select = await renderWithOne()
    fireEvent.change(select, { target: { value: 'OFFER' } })

    await waitFor(() => expect(changeStatus).toHaveBeenCalledWith('app-1', { status: 'OFFER', force: true }))
    expect(confirm).toHaveBeenCalledTimes(1)
  })

  it('does nothing when the forced change is not confirmed', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(false)
    const select = await renderWithOne()
    fireEvent.change(select, { target: { value: 'OFFER' } })
    expect(changeStatus).not.toHaveBeenCalled()
  })

  it('shows the backend message when the transition is rejected', async () => {
    list.mockResolvedValue(pageOf([makeApplication()]))
    changeStatus.mockRejectedValue(
      new ApiError({ status: 409, code: 'INVALID_STATUS_TRANSITION', message: 'DISCOVERED -> QUALIFIED is not allowed' }),
    )
    renderPage()
    const select = await screen.findByLabelText('Change status of Backend Developer')
    fireEvent.change(select, { target: { value: 'QUALIFIED' } })
    expect(await screen.findByText('DISCOVERED -> QUALIFIED is not allowed')).toBeInTheDocument()
  })
})
