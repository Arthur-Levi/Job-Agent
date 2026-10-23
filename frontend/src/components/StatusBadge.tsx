import { labelize } from '../utils/format'
import { statusClasses } from '../utils/status'

export function StatusBadge({ status }: { status: string }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset ${statusClasses(status)}`}
    >
      {labelize(status)}
    </span>
  )
}
