import { describe, expect, it } from 'vitest'
import { safeHttpUrl } from './url'
import { ApiError } from '../services/http'
import { describeError, fieldErrorsFrom } from './errors'
import {
  blankToNull,
  dateInputToIso,
  formatDate,
  formatSalary,
  isoToDateInput,
  labelize,
} from './format'

describe('format', () => {
  it('labelizes enum values', () => {
    expect(labelize('FULL_TIME')).toBe('Full time')
    expect(labelize('OPEN')).toBe('Open')
  })

  it('converts between <input type=date> and UTC ISO without shifting the day', () => {
    expect(dateInputToIso('2026-10-01')).toBe('2026-10-01T00:00:00Z')
    expect(dateInputToIso('')).toBeNull()
    expect(isoToDateInput('2026-10-01T00:00:00+00:00')).toBe('2026-10-01')
    expect(isoToDateInput(null)).toBe('')
  })

  it('formats missing and invalid dates as a dash', () => {
    expect(formatDate(null)).toBe('—')
    expect(formatDate('not a date')).toBe('—')
    expect(formatDate('2026-10-01T12:00:00Z')).toContain('2026')
  })

  it('formats salary ranges for display only', () => {
    expect(formatSalary(null, null, null)).toBe('—')
    expect(formatSalary('5000.00', '8000.00', 'BRL')).toMatch(/5,?000.*–.*8,?000/)
    expect(formatSalary('5000.00', null, 'BRL')).toMatch(/^from /)
    expect(formatSalary(null, '8000.00', 'BRL')).toMatch(/^up to /)
  })

  it('blankToNull trims', () => {
    expect(blankToNull('  ')).toBeNull()
    expect(blankToNull(' x ')).toBe('x')
  })
})

describe('errors', () => {
  it('describes API, connection and unknown errors', () => {
    const api = new ApiError({ status: 409, code: 'X', message: 'Conflict', requestId: 'rid-12345678' })
    expect(describeError(api)).toEqual({ title: 'Request failed', message: 'Conflict', requestId: 'rid-12345678' })
    expect(describeError(new ApiError({ status: 0, code: 'NETWORK_ERROR', message: 'down' })).title).toBe('Connection problem')
    expect(describeError(new ApiError({ status: 500, code: 'INTERNAL_ERROR', message: 'x' })).title).toBe('Server error')
    expect(describeError('boom').title).toBe('Unexpected error')
  })

  it('maps 422 validation details to fields', () => {
    const error = new ApiError({
      status: 422,
      code: 'VALIDATION_ERROR',
      message: 'invalid',
      details: [
        { loc: ['body', 'title'], message: 'String should have at least 1 character', type: 'x' },
        { loc: ['body', 'title'], message: 'second message ignored', type: 'x' },
        { loc: ['body', 'source_url'], message: 'Input should be a valid URL', type: 'y' },
      ],
    })
    expect(fieldErrorsFrom(error)).toEqual({
      title: 'String should have at least 1 character',
      source_url: 'Input should be a valid URL',
    })
  })

  it('ignores non-validation errors', () => {
    expect(fieldErrorsFrom(new ApiError({ status: 409, code: 'CONFLICT', message: 'x' }))).toEqual({})
    expect(fieldErrorsFrom(new Error('x'))).toEqual({})
  })
})

describe('safeHttpUrl', () => {
  it('only lets http(s) through', () => {
    expect(safeHttpUrl('https://jobs.example.com/1')).toBe('https://jobs.example.com/1')
    expect(safeHttpUrl('http://example.com')).toBe('http://example.com/')
    for (const bad of ['javascript:alert(1)', 'data:text/html,<script>', 'ftp://x.com', 'not a url', '', null, undefined]) {
      expect(safeHttpUrl(bad)).toBeNull()
    }
  })
})
