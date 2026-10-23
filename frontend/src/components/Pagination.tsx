import { Button } from './Button'

interface PaginationProps {
  total: number
  limit: number
  offset: number
  onChange: (offset: number) => void
}

export function Pagination({ total, limit, offset, onChange }: PaginationProps) {
  if (total === 0) return null
  const first = offset + 1
  const last = Math.min(offset + limit, total)
  return (
    <nav aria-label="Pagination" className="mt-3 flex items-center justify-between text-sm text-slate-400">
      <span>
        {first}–{last} of {total}
      </span>
      <div className="flex gap-2">
        <Button variant="secondary" disabled={offset === 0} onClick={() => onChange(Math.max(0, offset - limit))}>
          Previous
        </Button>
        <Button variant="secondary" disabled={offset + limit >= total} onClick={() => onChange(offset + limit)}>
          Next
        </Button>
      </div>
    </nav>
  )
}
