import { Link } from 'react-router-dom'
import { StatusBadge } from '../../components/StatusBadge'
import type { Application } from '../../types/api'
import { formatDate } from '../../utils/format'
import { StatusChanger } from './StatusChanger'

interface ApplicationsTableProps {
  applications: Application[]
  onChanged: () => void
}

export function ApplicationsTable({ applications, onChanged }: ApplicationsTableProps) {
  return (
    <div className="overflow-x-auto rounded-lg border border-slate-800">
      <table className="w-full min-w-[720px] text-left text-sm">
        <thead className="bg-slate-900 text-xs uppercase tracking-wide text-slate-500">
          <tr>
            <th scope="col" className="px-3 py-2">Job</th>
            <th scope="col" className="px-3 py-2">Company</th>
            <th scope="col" className="px-3 py-2">Status</th>
            <th scope="col" className="px-3 py-2">Applied</th>
            <th scope="col" className="px-3 py-2">Move to</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-800">
          {applications.map((application) => (
            <tr key={application.id} className="align-top hover:bg-slate-900/60">
              <td className="px-3 py-2">
                <Link to={`/jobs/${application.job.id}`} className="font-medium text-sky-400 hover:underline">
                  {application.job.title}
                </Link>
              </td>
              <td className="px-3 py-2">{application.job.company}</td>
              <td className="px-3 py-2"><StatusBadge status={application.status} /></td>
              <td className="px-3 py-2 text-slate-400">{formatDate(application.applied_at)}</td>
              <td className="px-3 py-2">
                <StatusChanger application={application} onChanged={onChanged} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
