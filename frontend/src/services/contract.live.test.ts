/**
 * Teste de CONTRATO contra um backend REAL. Fica desligado por padrão.
 *
 *   Only after verifying the API's disposable DB binding:
 *   VITE_LIVE_DISPOSABLE_ACK=jobagent_react_test VITE_LIVE_CONTRACT=1 \
 *     VITE_API_URL=http://127.0.0.1:18081 npm test -- contract
 *
 * Grava dados no banco do backend alvo: aponte para um banco descartável.
 * Detecta divergência entre os tipos TypeScript e o que a API realmente devolve.
 */
import { afterAll, beforeAll, describe, expect, it } from 'vitest'
import {
  APPLICATION_STATUSES,
  EMPLOYMENT_TYPES,
  JOB_STATUSES,
  SENIORITIES,
  WORK_MODELS,
} from '../types/api'
import { fieldErrorsFrom } from '../utils/errors'
import { applicationsApi } from './applicationsApi'
import { authApi } from './authApi'
import { ApiError, getBaseUrl } from './http'
import { jobsApi } from './jobsApi'
import { profileApi } from './profileApi'

const live = import.meta.env.VITE_LIVE_CONTRACT === '1'
const unique = Math.random().toString(36).slice(2, 10)

async function rejection(promise: Promise<unknown>): Promise<ApiError> {
  const error = await promise.then(
    () => null,
    (e: unknown) => e,
  )
  expect(error).toBeInstanceOf(ApiError)
  return error as ApiError
}

describe.skipIf(!live)('API contract (live backend)', () => {
  beforeAll(async () => {
    const baseUrl = getBaseUrl()
    const loopback = /^http:\/\/(127\.0\.0\.1|localhost):[0-9]+$/.test(baseUrl)
    if (!loopback || import.meta.env.VITE_LIVE_DISPOSABLE_ACK !== 'jobagent_react_test') {
      throw new Error('Live contract requires loopback API and acknowledgement of jobagent_react_test')
    }
    const testEmail = `d2e1-live-${Date.now()}-${unique}@example.invalid`
    const password = `Live-only-${Date.now()}-${unique}-pass!`
    await authApi.register({ name: 'D2 E1 Synthetic Contract', email: testEmail, password })
    await authApi.login({ email: testEmail, password })
  })

  afterAll(async () => {
    if (authApi.hasSession()) await authApi.logout()
  })

  it('enums in the frontend match the backend OpenAPI', async () => {
    const spec = (await (await fetch(`${getBaseUrl()}/openapi.json`)).json()) as {
      components: { schemas: Record<string, { enum?: string[] }> }
    }
    const enumOf = (name: string) => spec.components.schemas[name]?.enum
    expect(enumOf('ApplicationStatus')).toEqual([...APPLICATION_STATUSES])
    expect(enumOf('JobStatus')).toEqual([...JOB_STATUSES])
    expect(enumOf('WorkModel')).toEqual([...WORK_MODELS])
    expect(enumOf('Seniority')).toEqual([...SENIORITIES])
    expect(enumOf('EmploymentType')).toEqual([...EMPLOYMENT_TYPES])
  })

  it('profile: null before creation, then create/get/update with the declared shape', async () => {
    const existing = await profileApi.get()
    const saved = existing
      ? await profileApi.update({ headline: `Dev ${unique}`, city: null })
      : await profileApi.create({ headline: `Dev ${unique}`, desired_work_model: 'REMOTE' })
    expect(saved.headline).toBe(`Dev ${unique}`)
    expect(Object.keys(saved).sort()).toEqual(
      [
        'city', 'country', 'created_at', 'desired_seniority', 'desired_work_model',
        'headline', 'id', 'state', 'summary', 'updated_at',
      ].sort(),
    )
    expect((await profileApi.get())?.id).toBe(saved.id)
  })

  it('jobs: money as strings, null clears, pagination envelope, error mapping', async () => {
    const job = await jobsApi.create({
      title: `Backend ${unique}`,
      company: 'ACME',
      description: 'Build APIs.',
      source_url: `https://jobs.example.com/${unique}`,
      salary_min: '5000',
      salary_max: '8000.5',
      currency: 'BRL',
      published_at: '2026-10-01T00:00:00Z',
      location: 'Remote',
    })
    expect(job.salary_min).toBe('5000.00')
    expect(job.salary_max).toBe('8000.50')
    expect(job.status).toBe('OPEN')
    expect(Object.keys(job).sort()).toEqual(
      [
        'company', 'created_at', 'currency', 'description', 'employment_type', 'id', 'location',
        'published_at', 'salary_max', 'salary_min', 'seniority', 'source', 'source_url', 'status',
        'title', 'updated_at', 'work_model',
      ].sort(),
    )

    const updated = await jobsApi.update(job.id, { location: null, status: 'CLOSED' })
    expect(updated.location).toBeNull()
    expect(updated.status).toBe('CLOSED')

    const page = await jobsApi.list({ limit: 5, offset: 0, status: 'CLOSED' })
    expect(Object.keys(page).sort()).toEqual(['items', 'limit', 'offset', 'total'])
    expect(page.items.some((item) => item.id === job.id)).toBe(true)

    const missing = await rejection(jobsApi.get('00000000-0000-4000-8000-000000000000'))
    expect(missing).toMatchObject({ status: 404, code: 'JOB_NOT_FOUND' })
    expect(missing.requestId).toBeTruthy()

    const invalid = await rejection(jobsApi.create({ title: '   ', company: 'x', description: 'y' }))
    expect(invalid.code).toBe('VALIDATION_ERROR')
    expect(fieldErrorsFrom(invalid)).toHaveProperty('title')

    const duplicate = await rejection(
      jobsApi.create({ title: 'Again', company: 'x', description: 'y', source_url: `https://jobs.example.com/${unique}` }),
    )
    expect(duplicate.code).toBe('JOB_SOURCE_URL_EXISTS')
  })

  it('applications: allowed_next_statuses, events, forced changes and delete protection', async () => {
    const job = await jobsApi.create({ title: `Pipeline ${unique}`, company: 'ACME', description: 'd' })
    const created = await applicationsApi.create(job.id)

    expect(created.status).toBe('DISCOVERED')
    expect(created.allowed_next_statuses).toEqual(['QUALIFIED', 'WITHDRAWN'])
    expect(created.job).toEqual({ id: job.id, title: job.title, company: 'ACME' })
    expect(created.events).toHaveLength(1)
    expect(created.events[0]).toMatchObject({ event_type: 'CREATED', from_status: null, to_status: 'DISCOVERED' })
    expect(created.events[0]).toHaveProperty('metadata')

    const qualified = await applicationsApi.changeStatus(created.id, { status: 'QUALIFIED' })
    expect(qualified.allowed_next_statuses).toEqual(['PREPARED', 'WITHDRAWN'])

    const rejected = await rejection(applicationsApi.changeStatus(created.id, { status: 'OFFER' }))
    expect(rejected).toMatchObject({ status: 409, code: 'INVALID_STATUS_TRANSITION' })
    expect(rejected.details).toMatchObject({ from: 'QUALIFIED', to: 'OFFER' })

    const forced = await applicationsApi.changeStatus(created.id, { status: 'OFFER', force: true })
    expect(forced.status).toBe('OFFER')
    expect(forced.events.at(-1)).toMatchObject({ event_type: 'STATUS_CHANGED', metadata: { forced: true } })

    const page = await applicationsApi.list({ status: 'OFFER', job_id: job.id })
    expect(page.items.map((item) => item.id)).toEqual([created.id])

    const protectedDelete = await rejection(jobsApi.remove(job.id))
    expect(protectedDelete.code).toBe('JOB_HAS_APPLICATIONS')
  })

  it('delete returns nothing (204) for a job without applications', async () => {
    const job = await jobsApi.create({ title: `Disposable ${unique}`, company: 'ACME', description: 'd' })
    await expect(jobsApi.remove(job.id)).resolves.toBeUndefined()
  })
})
