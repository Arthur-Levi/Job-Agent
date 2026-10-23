import { useCallback, useState } from 'react'
import type { ReactNode } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { AsyncView } from '../components/AsyncView'
import { Button } from '../components/Button'
import { Card } from '../components/Card'
import { PageHeader } from '../components/PageHeader'
import { ErrorBanner } from '../components/States'
import { StatusBadge } from '../components/StatusBadge'
import { JobApplicationPanel } from '../features/jobs/JobApplicationPanel'
import { JobForm } from '../features/jobs/JobForm'
import { useApiQuery } from '../hooks/useApiQuery'
import { useSubmit } from '../hooks/useSubmit'
import { jobsApi } from '../services/jobsApi'
import type { Job } from '../types/api'
import { formatDate, formatSalary, labelize } from '../utils/format'
import { safeHttpUrl } from '../utils/url'

function Fact({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div>
      <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</dt>
      <dd className="mt-0.5 text-sm text-slate-200">{children || '—'}</dd>
    </div>
  )
}

function JobFacts({ job }: { job: Job }) {
  const sourceHref = safeHttpUrl(job.source_url)
  return (
    <Card>
      <dl className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <Fact label="Location">{job.location}</Fact>
        <Fact label="Work model">{job.work_model ? labelize(job.work_model) : null}</Fact>
        <Fact label="Employment">{job.employment_type ? labelize(job.employment_type) : null}</Fact>
        <Fact label="Seniority">{job.seniority ? labelize(job.seniority) : null}</Fact>
        <Fact label="Salary">{formatSalary(job.salary_min, job.salary_max, job.currency)}</Fact>
        <Fact label="Published">{formatDate(job.published_at)}</Fact>
        <Fact label="Source">
          {sourceHref ? (
            <a href={sourceHref} target="_blank" rel="noopener noreferrer" className="text-sky-400 hover:underline">
              {job.source ?? sourceHref}
            </a>
          ) : (
            job.source
          )}
        </Fact>
        <Fact label="Added">{formatDate(job.created_at)}</Fact>
      </dl>
    </Card>
  )
}

export function JobDetailPage() {
  const { jobId = '' } = useParams()
  const navigate = useNavigate()
  const [editing, setEditing] = useState(false)
  const remove = useSubmit()

  const fetcher = useCallback((signal: AbortSignal) => jobsApi.get(jobId, signal), [jobId])
  const query = useApiQuery(fetcher)

  async function handleDelete() {
    if (!window.confirm('Delete this job? This cannot be undone.')) return
    const result = await remove.submit(() => jobsApi.remove(jobId))
    if (result.ok) navigate('/jobs')
  }

  return (
    <>
      <p className="mb-3 text-sm">
        <Link to="/jobs" className="text-sky-400 hover:underline">← Back to jobs</Link>
      </p>
      <AsyncView query={query} loadingLabel="Loading job…">
        {(job) =>
          editing ? (
            <Card>
              <h2 className="mb-3 text-sm font-semibold text-slate-200">Edit job</h2>
              <JobForm
                job={job}
                onCancel={() => setEditing(false)}
                onSaved={() => {
                  setEditing(false)
                  query.reload()
                }}
              />
            </Card>
          ) : (
            <div className="space-y-4">
              <PageHeader
                title={job.title}
                subtitle={job.company}
                actions={
                  <>
                    <StatusBadge status={job.status} />
                    <Button variant="secondary" onClick={() => setEditing(true)}>Edit</Button>
                    <Button variant="danger" onClick={handleDelete} disabled={remove.submitting}>Delete</Button>
                  </>
                }
              />
              {remove.error ? <ErrorBanner error={remove.error} /> : null}
              <JobFacts job={job} />
              <Card>
                <h2 className="mb-2 text-sm font-semibold text-slate-200">Description</h2>
                <p className="whitespace-pre-wrap text-sm leading-relaxed text-slate-300">{job.description}</p>
              </Card>
              <JobApplicationPanel jobId={job.id} />
            </div>
          )
        }
      </AsyncView>
    </>
  )
}
