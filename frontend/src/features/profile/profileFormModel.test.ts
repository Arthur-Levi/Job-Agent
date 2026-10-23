import { describe, expect, it } from 'vitest'
import { makeProfile } from '../../test/fixtures'
import { toProfileInput, toProfileValues } from './profileFormModel'

describe('profile form model', () => {
  it('starts empty when there is no profile', () => {
    expect(toProfileInput(toProfileValues(null))).toEqual({
      headline: null,
      summary: null,
      city: null,
      state: null,
      country: null,
      desired_work_model: null,
      desired_seniority: null,
    })
  })

  it('sends null for fields the user cleared (so PATCH clears them)', () => {
    const values = { ...toProfileValues(makeProfile()), city: '  ', desired_work_model: '' as const }
    const input = toProfileInput(values)
    expect(input.city).toBeNull()
    expect(input.desired_work_model).toBeNull()
    expect(input.headline).toBe('Backend developer')
  })
})
