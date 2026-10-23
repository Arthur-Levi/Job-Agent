import { useCallback } from 'react'
import { useSearchParams } from 'react-router-dom'

/** Filtro guardado na URL (?key=VALOR): compartilhável e sobrevive ao reload. Valores inválidos são ignorados. */
export function useUrlFilter<T extends string>(
  key: string,
  valid: readonly T[],
): [T | undefined, (value: T | undefined) => void] {
  const [params, setParams] = useSearchParams()
  const raw = params.get(key)
  const value = raw !== null && (valid as readonly string[]).includes(raw) ? (raw as T) : undefined

  const set = useCallback(
    (next: T | undefined) => {
      setParams(
        (previous) => {
          const copy = new URLSearchParams(previous)
          if (next) copy.set(key, next)
          else copy.delete(key)
          return copy
        },
        { replace: true },
      )
    },
    [key, setParams],
  )
  return [value, set]
}
