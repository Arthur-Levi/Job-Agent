import type { Profile, ProfileInput } from '../types/api'
import { ApiError, request } from './http'

export const profileApi = {
  /** Devolve null quando o perfil ainda não existe (404 PROFILE_NOT_FOUND é estado normal). */
  async get(signal?: AbortSignal): Promise<Profile | null> {
    try {
      return await request<Profile>('GET', '/api/v1/profile', { signal })
    } catch (error) {
      if (error instanceof ApiError && error.code === 'PROFILE_NOT_FOUND') return null
      throw error
    }
  },
  create: (input: Partial<ProfileInput>) =>
    request<Profile>('POST', '/api/v1/profile', { body: input }),
  update: (input: Partial<ProfileInput>) =>
    request<Profile>('PATCH', '/api/v1/profile', { body: input }),
}
