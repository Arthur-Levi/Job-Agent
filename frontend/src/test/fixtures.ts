import type { Application, Job, Page, Profile } from '../types/api'

export function makeJob(overrides: Partial<Job> = {}): Job {
  return {
    id: 'job-1',
    title: 'Backend Developer',
    company: 'ACME',
    description: 'Build APIs.\nSecond line.',
    source: null,
    source_url: null,
    location: 'Remote',
    work_model: null,
    employment_type: null,
    seniority: null,
    salary_min: null,
    salary_max: null,
    currency: null,
    published_at: null,
    status: 'OPEN',
    created_at: '2026-10-01T12:00:00Z',
    updated_at: '2026-10-01T12:00:00Z',
    ...overrides,
  }
}

export function makeApplication(overrides: Partial<Application> = {}): Application {
  return {
    id: 'app-1',
    job_id: 'job-1',
    job: { id: 'job-1', title: 'Backend Developer', company: 'ACME' },
    status: 'DISCOVERED',
    applied_at: null,
    notes: null,
    allowed_next_statuses: ['QUALIFIED', 'WITHDRAWN'],
    created_at: '2026-10-01T12:00:00Z',
    updated_at: '2026-10-01T12:00:00Z',
    ...overrides,
  }
}

export function makeProfile(overrides: Partial<Profile> = {}): Profile {
  return {
    id: 'profile-1',
    headline: 'Backend developer',
    summary: null,
    city: 'São Paulo',
    state: null,
    country: 'Brasil',
    desired_work_model: 'REMOTE',
    desired_seniority: null,
    created_at: '2026-10-01T12:00:00Z',
    updated_at: '2026-10-01T12:00:00Z',
    ...overrides,
  }
}

export function pageOf<T>(items: T[], total = items.length, offset = 0): Page<T> {
  return { items, total, limit: 20, offset }
}
