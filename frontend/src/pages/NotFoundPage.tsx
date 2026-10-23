import { Link } from 'react-router-dom'
import { EmptyState } from '../components/States'

export function NotFoundPage() {
  return (
    <EmptyState
      title="Page not found"
      description="The page you are looking for does not exist."
      action={
        <Link to="/dashboard" className="rounded-md bg-sky-500 px-3 py-1.5 text-sm font-medium text-slate-950 hover:bg-sky-400">
          Back to dashboard
        </Link>
      }
    />
  )
}
