import { describe, expect, it } from 'vitest'
import { makeJob } from '../../test/fixtures'
import { toJobInput, toJobValues, validateJob } from './jobFormModel'

function values(overrides: Partial<ReturnType<typeof toJobValues>> = {}) {
  return { ...toJobValues(), title: 'Dev', company: 'ACME', description: 'Text', ...overrides }
}

describe('validateJob', () => {
  it('requires title, company and description', () => {
    expect(Object.keys(validateJob(toJobValues())).sort()).toEqual(['company', 'description', 'title'])
  })

  it('accepts a minimal valid job', () => {
    expect(validateJob(values())).toEqual({})
  })

  it('checks salary rules', () => {
    expect(validateJob(values({ salary_min: 'abc', currency: 'BRL' })).salary_min).toBeDefined()
    expect(validateJob(values({ salary_min: '-1', currency: 'BRL' })).salary_min).toBeDefined()
    expect(validateJob(values({ salary_min: '9000', salary_max: '5000', currency: 'BRL' })).salary_max).toBeDefined()
    expect(validateJob(values({ salary_min: '5000' })).currency).toBe('Required when a salary is set')
    expect(validateJob(values({ currency: 'REAL' })).currency).toBeDefined()
    expect(validateJob(values({ salary_min: '5000', salary_max: '5000', currency: 'brl' }))).toEqual({})
  })
})

describe('toJobInput', () => {
  it('normalizes: trims, blank -> null, uppercases currency, date -> UTC ISO', () => {
    const input = toJobInput(
      values({
        title: '  Dev  ',
        location: '   ',
        currency: 'brl',
        salary_min: '5000',
        published_at: '2026-10-01',
        work_model: 'REMOTE',
      }),
    )
    expect(input).toMatchObject({
      title: 'Dev',
      location: null,
      currency: 'BRL',
      salary_min: '5000',
      salary_max: null,
      published_at: '2026-10-01T00:00:00Z',
      work_model: 'REMOTE',
      seniority: null,
      status: 'OPEN',
    })
  })

  it('round-trips an existing job without altering it', () => {
    const job = makeJob({
      salary_min: '5000.00',
      salary_max: '8000.00',
      currency: 'BRL',
      published_at: '2026-10-01T00:00:00+00:00',
      source_url: 'https://jobs.example.com/1',
    })
    const input = toJobInput(toJobValues(job))
    expect(input.salary_min).toBe('5000.00')
    expect(input.published_at).toBe('2026-10-01T00:00:00Z')
    expect(input.source_url).toBe('https://jobs.example.com/1')
  })
})
