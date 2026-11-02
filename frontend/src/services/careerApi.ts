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

export interface DiagnosticEvidence {
  fact_id: string
  title: string
  verification: string
}

export interface DiagnosticCoverage {
  category: 'experience' | 'education' | 'project' | 'skill'
  title: string
  state: 'documented' | 'not_documented'
  count: number
  evidence: DiagnosticEvidence[]
}

export interface DiagnosticAction {
  kind: 'review_documented_fact' | 'verify_missing_records'
  priority: 'high' | 'normal'
  message: string
  next_step: string
  evidence_fact_ids: string[]
  fact_id?: string
  category?: string
  fields?: string[]
}

export interface CareerDiagnostic {
  status: 'preliminary'
  basis: 'active_fact_ledger'
  total_active_facts: number
  coverage: DiagnosticCoverage[]
  review_actions: DiagnosticAction[]
  limitations: string[]
}

export const careerApi = {
  diagnostic: (signal?: AbortSignal) =>
    request<CareerDiagnostic>('GET', '/api/v1/career/diagnostic', { signal }),
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
