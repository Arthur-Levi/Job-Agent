import { act, renderHook, waitFor } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { useApiQuery } from './useApiQuery'
import type { Fetcher } from './useApiQuery'

function deferred<T>() {
  let resolve!: (value: T) => void
  let reject!: (reason: unknown) => void
  const promise = new Promise<T>((res, rej) => {
    resolve = res
    reject = rej
  })
  return { promise, resolve, reject }
}

describe('useApiQuery', () => {
  it('goes loading -> success', async () => {
    const fetcher: Fetcher<string> = () => Promise.resolve('data')
    const { result } = renderHook(() => useApiQuery(fetcher))
    expect(result.current.state.status).toBe('loading')
    await waitFor(() => expect(result.current.state).toEqual({ status: 'success', data: 'data' }))
  })

  it('goes loading -> error', async () => {
    const boom = new Error('boom')
    const fetcher: Fetcher<string> = () => Promise.reject(boom)
    const { result } = renderHook(() => useApiQuery(fetcher))
    await waitFor(() => expect(result.current.state).toEqual({ status: 'error', error: boom }))
  })

  it('reload keeps the previous data visible while refreshing', async () => {
    const first = deferred<string>()
    const second = deferred<string>()
    const queue = [first, second]
    const fetcher: Fetcher<string> = () => {
      const next = queue.shift()
      if (!next) throw new Error('unexpected call')
      return next.promise
    }
    const { result } = renderHook(() => useApiQuery(fetcher))

    await act(async () => first.resolve('v1'))
    await waitFor(() => expect(result.current.state).toEqual({ status: 'success', data: 'v1' }))

    act(() => result.current.reload())
    expect(result.current.refreshing).toBe(true)
    expect(result.current.state).toEqual({ status: 'success', data: 'v1' })

    await act(async () => second.resolve('v2'))
    await waitFor(() => expect(result.current.state).toEqual({ status: 'success', data: 'v2' }))
    expect(result.current.refreshing).toBe(false)
  })

  it('a new fetcher goes back to loading and discards the stale response', async () => {
    const slow = deferred<string>()
    const slowFetcher: Fetcher<string> = () => slow.promise
    const fastFetcher: Fetcher<string> = () => Promise.resolve('fast')

    const { result, rerender } = renderHook(({ fetcher }) => useApiQuery(fetcher), {
      initialProps: { fetcher: slowFetcher },
    })
    rerender({ fetcher: fastFetcher })
    await waitFor(() => expect(result.current.state).toEqual({ status: 'success', data: 'fast' }))

    await act(async () => slow.resolve('stale')) // chega atrasada: não pode sobrescrever
    expect(result.current.state).toEqual({ status: 'success', data: 'fast' })
  })
})
