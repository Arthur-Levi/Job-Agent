import { Link } from 'react-router-dom'
import { StatusBadge } from '../../components/StatusBadge'
import type { Job } from '../../types/api'
import { formatDate } from '../../utils/format'

export function JobsTable({ jobs }: { jobs: Job[] }) {
  return (
    <div className="overflow-x-auto rounded-lg border border-slate-800">
      <table className="w-full min-w-[640px] text-left text-sm">
        <thead className="bg-slate-900 text-xs uppercase tracking-wide text-slate-500">
          <tr>
            <th scope="col" className="px-3 py-2">Job</th>
            <th scope="col" className="px-3 py-2">Company</th>
            <th scope="col" className="px-3 py-2">Location</th>
            <th scope="col" className="px-3 py-2">Status</th>
            <th scope="col" className="px-3 py-2">Date</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-800">
          {jobs.map((job) => (
            <tr key={job.id} className="hover:bg-slate-900/60">
              <td className="px-3 py-2">
                <Link to={`/jobs/${job.id}`} className="font-medium text-sky-400 hover:underline">
                  {job.title}
                </Link>
              </td>
              <td className="px-3 py-2">{job.company}</td>
              <td className="px-3 py-2 text-slate-400">{job.location ?? '—'}</td>
              <td className="px-3 py-2"><StatusBadge status={job.status} /></td>
              <td className="px-3 py-2 text-slate-400">{formatDate(job.published_at ?? job.created_at)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
