import { useCallback } from 'react'
import { Link } from 'react-router-dom'
import { AsyncView } from '../../components/AsyncView'
import { Button } from '../../components/Button'
import { Card } from '../../components/Card'
import { ErrorBanner } from '../../components/States'
import { StatusBadge } from '../../components/StatusBadge'
import { useApiQuery } from '../../hooks/useApiQuery'
import { useSubmit } from '../../hooks/useSubmit'
import { applicationsApi } from '../../services/applicationsApi'

/** Mostra se a vaga já está no pipeline e permite começar a acompanhá-la. */
export function JobApplicationPanel({ jobId }: { jobId: string }) {
  const fetcher = useCallback(
    (signal: AbortSignal) => applicationsApi.list({ job_id: jobId, limit: 1 }, signal),
    [jobId],
  )
  const query = useApiQuery(fetcher)
  const { submitting, error, submit } = useSubmit()

  async function track() {
    const result = await submit(() => applicationsApi.create(jobId))
    if (result.ok) query.reload()
  }

  return (
    <Card>
      <h2 className="mb-2 text-sm font-semibold text-slate-200">Application</h2>
      <AsyncView query={query} loadingLabel="Checking pipeline…">
        {(page) => {
          const application = page.items[0]
          if (application) {
            return (
              <div className="flex flex-wrap items-center gap-3 text-sm">
                <StatusBadge status={application.status} />
                <Link to="/applications" className="text-sky-400 hover:underline">
                  Open pipeline
                </Link>
              </div>
            )
          }
          return (
            <div className="space-y-3">
              <p className="text-sm text-slate-400">This job is not in your pipeline yet.</p>
              {error ? <ErrorBanner error={error} /> : null}
              <Button onClick={track} disabled={submitting}>
                {submitting ? 'Adding…' : 'Track application'}
              </Button>
            </div>
          )
        }}
      </AsyncView>
    </Card>
  )
}
