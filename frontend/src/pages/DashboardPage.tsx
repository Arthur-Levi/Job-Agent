import { Link } from 'react-router-dom'
import { AsyncView } from '../components/AsyncView'
import { Card } from '../components/Card'
import { PageHeader } from '../components/PageHeader'
import { fetchDashboardCounts } from '../features/dashboard/counts'
import type { DashboardCounts } from '../features/dashboard/counts'
import { useApiQuery } from '../hooks/useApiQuery'

interface MetricProps {
  label: string
  value: number
  to: string
}

function Metric({ label, value, to }: MetricProps) {
  return (
    <Link
      to={to}
      className="rounded-lg border border-slate-800 bg-slate-900/60 p-4 transition-colors hover:border-sky-500/50 focus:outline-none focus-visible:ring-2 focus-visible:ring-sky-400"
    >
      <div className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</div>
      <div className="mt-2 text-3xl font-semibold tabular-nums text-slate-100">{value}</div>
    </Link>
  )
}

function Overview({ counts }: { counts: DashboardCounts }) {
  const nothingYet = counts.jobs === 0 && counts.applications === 0
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Metric label="Jobs" value={counts.jobs} to="/jobs" />
        <Metric label="Applications" value={counts.applications} to="/applications" />
        <Metric label="Ready" value={counts.ready} to="/applications?status=READY" />
        <Metric label="Interviews" value={counts.interviews} to="/applications" />
      </div>
      {nothingYet ? (
        <Card>
          <p className="text-sm text-slate-400">
            Nothing here yet.{' '}
            <Link to="/jobs" className="text-sky-400 hover:underline">
              Add your first job
            </Link>{' '}
            to start tracking opportunities.
          </p>
        </Card>
      ) : null}
    </div>
  )
}

export function DashboardPage() {
  const query = useApiQuery(fetchDashboardCounts)
  return (
    <>
      <PageHeader title="JOB COMMAND" subtitle="Live counts from your database." />
      <AsyncView query={query} loadingLabel="Loading overview…">
        {(counts) => <Overview counts={counts} />}
      </AsyncView>
    </>
  )
}
