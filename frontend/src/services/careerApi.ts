import { request } from './http'

export interface CareerFact {
  id: string
  subject: string
  predicate: string
  value: string
  status: string
  verification: string
  source_reference: string
  supersedes_id: string | null
}

export interface CareerProfile {
  profile_id: string | null
  items: Array<{
    id: string
    category: string
    title: string
    source_fact_ids: string[]
    verification: string
  }>
}

export const careerApi = {
  profile: (signal?: AbortSignal) =>
    request<CareerProfile>('GET', '/api/v1/career/profile', { signal }),
  facts: (includeHistory: boolean, signal?: AbortSignal) =>
    request<{ items: CareerFact[] }>('GET', '/api/v1/career/facts', {
      query: { include_history: includeHistory }, signal,
    }),
  correct: (id: string, value: string, reason: string) =>
    request<CareerFact>('POST', `/api/v1/career/facts/${encodeURIComponent(id)}/corrections`, {
      body: { value, reason },
    }),
}
