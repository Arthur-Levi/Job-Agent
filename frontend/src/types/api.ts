// Espelha os schemas Pydantic do backend (app/schemas). Dinheiro trafega como string.

export const WORK_MODELS = ['REMOTE', 'HYBRID', 'ONSITE'] as const
export const SENIORITIES = ['INTERN', 'JUNIOR', 'MID', 'SENIOR', 'LEAD'] as const
export const EMPLOYMENT_TYPES = [
  'FULL_TIME',
  'PART_TIME',
  'CONTRACT',
  'INTERNSHIP',
  'TEMPORARY',
  'FREELANCE',
] as const
export const JOB_STATUSES = ['OPEN', 'CLOSED', 'ARCHIVED'] as const
// Mesma ordem do enum ApplicationStatus no backend.
export const APPLICATION_STATUSES = [
  'DISCOVERED',
  'QUALIFIED',
  'PREPARED',
  'READY',
  'APPLIED',
  'RESPONSE',
  'INTERVIEW',
  'TECHNICAL',
  'OFFER',
  'REJECTED',
  'WITHDRAWN',
  'GHOSTED',
] as const

export type WorkModel = (typeof WORK_MODELS)[number]
export type Seniority = (typeof SENIORITIES)[number]
export type EmploymentType = (typeof EMPLOYMENT_TYPES)[number]
export type JobStatus = (typeof JOB_STATUSES)[number]
export type ApplicationStatus = (typeof APPLICATION_STATUSES)[number]
export type ApplicationEventType = 'CREATED' | 'STATUS_CHANGED' | 'NOTE_UPDATED'

export interface Page<T> {
  items: T[]
  total: number
  limit: number
  offset: number
}

export interface Profile {
  id: string
  headline: string | null
  summary: string | null
  city: string | null
  state: string | null
  country: string | null
  desired_work_model: WorkModel | null
  desired_seniority: Seniority | null
  created_at: string
  updated_at: string
}

export type ProfileInput = Omit<Profile, 'id' | 'created_at' | 'updated_at'>

export interface Job {
  id: string
  title: string
  company: string
  description: string
  source: string | null
  source_url: string | null
  location: string | null
  work_model: WorkModel | null
  employment_type: EmploymentType | null
  seniority: Seniority | null
  salary_min: string | null
  salary_max: string | null
  currency: string | null
  published_at: string | null
  status: JobStatus
  created_at: string
  updated_at: string
}

export type JobInput = Omit<Job, 'id' | 'created_at' | 'updated_at'>

export interface JobSummary {
  id: string
  title: string
  company: string
}

export interface Application {
  id: string
  job_id: string
  job: JobSummary
  status: ApplicationStatus
  applied_at: string | null
  notes: string | null
  allowed_next_statuses: ApplicationStatus[]
  created_at: string
  updated_at: string
}

export interface ApplicationEvent {
  id: string
  event_type: ApplicationEventType
  from_status: ApplicationStatus | null
  to_status: ApplicationStatus | null
  metadata: Record<string, unknown> | null
  created_at: string
}

export interface ApplicationDetail extends Application {
  events: ApplicationEvent[]
}

export interface ApplicationStatusChange {
  status: ApplicationStatus
  force?: boolean
}

export interface ListParams {
  limit?: number
  offset?: number
}
