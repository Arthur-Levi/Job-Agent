import { useCallback, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { AsyncView } from '../components/AsyncView'
import { Button } from '../components/Button'
import { Card } from '../components/Card'
import { SelectField } from '../components/Field'
import { PageHeader } from '../components/PageHeader'
import { Pagination } from '../components/Pagination'
import { EmptyState } from '../components/States'
import { JobForm } from '../features/jobs/JobForm'
import { JobsTable } from '../features/jobs/JobsTable'
import { useApiQuery } from '../hooks/useApiQuery'
import { useUrlFilter } from '../hooks/useUrlFilter'
import { jobsApi } from '../services/jobsApi'
import { JOB_STATUSES } from '../types/api'
import { labelize } from '../utils/format'

const PAGE_SIZE = 20
const STATUS_OPTIONS = JOB_STATUSES.map((value) => ({ value, label: labelize(value) }))

export function JobsPage() {
  const navigate = useNavigate()
  const [status, setStatus] = useUrlFilter('status', JOB_STATUSES)
  const [offset, setOffset] = useState(0)
  const [adding, setAdding] = useState(false)

  const fetcher = useCallback(
    (signal: AbortSignal) => jobsApi.list({ limit: PAGE_SIZE, offset, ...(status ? { status } : {}) }, signal),
    [offset, status],
  )
  const query = useApiQuery(fetcher)

  return (
    <>
      <PageHeader
        title="Jobs"
        subtitle="Opportunities you are tracking."
        actions={!adding ? <Button onClick={() => setAdding(true)}>Add Job</Button> : null}
      />

      {adding ? (
        <Card className="mb-5">
          <h2 className="mb-3 text-sm font-semibold text-slate-200">New job</h2>
          <JobForm
            onCancel={() => setAdding(false)}
            onSaved={(job) => {
              setAdding(false)
              navigate(`/jobs/${job.id}`)
            }}
          />
        </Card>
      ) : null}

      <div className="mb-3 max-w-[200px]">
        <SelectField
          label="Status"
          placeholder="All"
          options={STATUS_OPTIONS}
          value={status ?? ''}
          onChange={(e) => {
            setOffset(0)
            setStatus(e.target.value ? (e.target.value as (typeof JOB_STATUSES)[number]) : undefined)
          }}
        />
      </div>

      <AsyncView
        query={query}
        loadingLabel="Loading jobs…"
        isEmpty={(page) => page.total === 0}
        empty={
          status ? (
            <EmptyState title="No jobs match this filter" description="Try another status." />
          ) : (
            <EmptyState
              title="No jobs yet"
              description="Add the first job you want to track."
              action={<Button onClick={() => setAdding(true)}>Add Job</Button>}
            />
          )
        }
      >
        {(page) => (
          <>
            <JobsTable jobs={page.items} />
            <Pagination total={page.total} limit={page.limit} offset={page.offset} onChange={setOffset} />
          </>
        )}
      </AsyncView>
    </>
  )
}
