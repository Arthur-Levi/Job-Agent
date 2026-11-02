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

export type ResumeCategory = 'experience' | 'education' | 'project' | 'skill'

export interface ResumeDraftEntry {
  fact_id: string
  verification: string
  title: string
  description: string | null
  organization: string | null
  start_date: string | null
  end_date: string | null
  requires_review: boolean
}

export interface ResumeExportPreview {
  status: 'draft_requires_candidate_review'
  basis: 'active_fact_ledger'
  candidate_name: string
  approval_sha256: string
  approval_required: true
  page_limit: number
  export_formats: Array<'pdf' | 'docx'>
  sections: Array<{ category: ResumeCategory; entries: ResumeDraftEntry[] }>
  omitted: Array<{ fact_id: string; reason: string }>
  limitations: string[]
}

export interface VacancyRequirement {
  category: ResumeCategory | 'work_mode'
  name: string
  importance: 'required' | 'preferred'
}
export interface VacancyMatch {
  vacancy_title: string
  status: string
  vacancy_source: string
  requirements: Array<{
    position: number
    category: string
    name: string
    importance: string
    classification: 'documented_match' | 'not_documented' | 'explicit_incompatibility'
    evidence: Array<{ fact_id: string; title: string; verification: string }>
    explanation: string
    next_step: string
  }>
  summary: { total: number; documented_match: number; not_documented: number; explicit_incompatibility: number }
  limitations: string[]
}

export const careerApi = {
  exportPreview: (signal?: AbortSignal) =>
    request<ResumeExportPreview>('GET', '/api/v1/career/resume-export/preview', { signal }),
  vacancyMatch: (vacancy_title: string, requirements: VacancyRequirement[]) =>
    request<VacancyMatch>('POST', '/api/v1/career/vacancy-match', {
      body: { vacancy_title, requirements },
    }),
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
