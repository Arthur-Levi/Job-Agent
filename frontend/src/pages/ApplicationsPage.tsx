import { useCallback, useState } from 'react'
import { Link } from 'react-router-dom'
import { AsyncView } from '../components/AsyncView'
import { SelectField } from '../components/Field'
import { PageHeader } from '../components/PageHeader'
import { Pagination } from '../components/Pagination'
import { EmptyState } from '../components/States'
import { ApplicationsTable } from '../features/applications/ApplicationsTable'
import { useApiQuery } from '../hooks/useApiQuery'
import { useUrlFilter } from '../hooks/useUrlFilter'
import { applicationsApi } from '../services/applicationsApi'
import { APPLICATION_STATUSES } from '../types/api'
import type { ApplicationStatus } from '../types/api'
import { labelize } from '../utils/format'

const PAGE_SIZE = 20
const STATUS_OPTIONS = APPLICATION_STATUSES.map((value) => ({ value, label: labelize(value) }))

export function ApplicationsPage() {
  const [status, setStatus] = useUrlFilter('status', APPLICATION_STATUSES)
  const [offset, setOffset] = useState(0)

  const fetcher = useCallback(
    (signal: AbortSignal) =>
      applicationsApi.list({ limit: PAGE_SIZE, offset, ...(status ? { status } : {}) }, signal),
    [offset, status],
  )
  const query = useApiQuery(fetcher)

  return (
    <>
      <PageHeader title="Applications" subtitle="Your pipeline, most recent first." />

      <div className="mb-3 max-w-[200px]">
        <SelectField
          label="Status"
          placeholder="All"
          options={STATUS_OPTIONS}
          value={status ?? ''}
          onChange={(e) => {
            setOffset(0)
            setStatus(e.target.value ? (e.target.value as ApplicationStatus) : undefined)
          }}
        />
      </div>

      <AsyncView
        query={query}
        loadingLabel="Loading applications…"
        isEmpty={(page) => page.total === 0}
        empty={
          status ? (
            <EmptyState title="No applications with this status" description="Try another status." />
          ) : (
            <EmptyState
              title="No applications yet"
              description="Open a job and choose “Track application” to add it to the pipeline."
              action={
                <Link to="/jobs" className="rounded-md bg-sky-500 px-3 py-1.5 text-sm font-medium text-slate-950 hover:bg-sky-400">
                  Go to jobs
                </Link>
              }
            />
          )
        }
      >
        {(page) => (
          <>
            <ApplicationsTable applications={page.items} onChanged={query.reload} />
            <Pagination total={page.total} limit={page.limit} offset={page.offset} onChange={setOffset} />
          </>
        )}
      </AsyncView>
    </>
  )
}
