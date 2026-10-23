import { useCallback, useState } from 'react'

export type SubmitResult<T> = { ok: true; value: T } | { ok: false }

/** Estado de envio de formulário/ação: submitting + último erro. Nunca lança. */
export function useSubmit() {
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<unknown>(null)

  const submit = useCallback(async function run<T>(action: () => Promise<T>): Promise<SubmitResult<T>> {
    setSubmitting(true)
    setError(null)
    try {
      return { ok: true, value: await action() }
    } catch (caught) {
      setError(caught)
      return { ok: false }
    } finally {
      setSubmitting(false)
    }
  }, [])

  const clearError = useCallback(() => setError(null), [])
  return { submitting, error, submit, clearError }
}
