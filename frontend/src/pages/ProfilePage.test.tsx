import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { profileApi } from '../services/profileApi'
import { ApiError } from '../services/http'
import { makeProfile } from '../test/fixtures'
import { ProfilePage } from './ProfilePage'

vi.mock('../services/profileApi', () => ({
  profileApi: { get: vi.fn(), create: vi.fn(), update: vi.fn() },
}))

const get = vi.mocked(profileApi.get)

beforeEach(() => {
  vi.resetAllMocks()
})

describe('ProfilePage', () => {
  it('shows the empty state, then creates the profile', async () => {
    get.mockResolvedValueOnce(null)
    vi.mocked(profileApi.create).mockResolvedValue(makeProfile())
    get.mockResolvedValueOnce(makeProfile({ headline: 'Fresh profile' }))
    render(<ProfilePage />)

    expect(await screen.findByText('No profile yet')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Create profile' }))
    fireEvent.change(screen.getByLabelText('Headline'), { target: { value: 'Fresh profile' } })
    fireEvent.click(screen.getByRole('button', { name: 'Create profile' }))

    await waitFor(() => expect(profileApi.create).toHaveBeenCalledTimes(1))
    expect(vi.mocked(profileApi.create).mock.calls[0]?.[0]).toMatchObject({ headline: 'Fresh profile', city: null })
    expect(await screen.findByText('Fresh profile')).toBeInTheDocument()
  })

  it('shows the profile and edits it, sending null for cleared fields', async () => {
    get.mockResolvedValue(makeProfile({ headline: 'Backend developer', city: 'Recife' }))
    vi.mocked(profileApi.update).mockResolvedValue(makeProfile())
    render(<ProfilePage />)

    expect(await screen.findByText('Backend developer')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Edit profile' }))
    fireEvent.change(screen.getByLabelText('City'), { target: { value: '' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save changes' }))

    await waitFor(() => expect(profileApi.update).toHaveBeenCalledTimes(1))
    expect(vi.mocked(profileApi.update).mock.calls[0]?.[0]).toMatchObject({ city: null, headline: 'Backend developer' })
  })

  it('shows an error state when loading fails', async () => {
    get.mockRejectedValue(new ApiError({ status: 0, code: 'NETWORK_ERROR', message: 'Could not reach the API.' }))
    render(<ProfilePage />)
    expect(await screen.findByRole('alert')).toHaveTextContent('Could not reach the API.')
  })
})
