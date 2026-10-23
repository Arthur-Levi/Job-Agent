import type { ChangeEvent } from 'react'
import { useSubmit } from '../../hooks/useSubmit'
import { applicationsApi } from '../../services/applicationsApi'
import { APPLICATION_STATUSES } from '../../types/api'
import type { Application, ApplicationStatus } from '../../types/api'
import { describeError } from '../../utils/errors'
import { labelize } from '../../utils/format'

interface StatusChangerProps {
  application: Application
  /** Chamado após cada tentativa (sucesso ou falha) para recarregar o estado real. */
  onChanged: () => void
}

/**
 * Só oferece os destinos que o BACKEND informa (allowed_next_statuses): a política de
 * transições vive em um único lugar. As demais opções exigem confirmação e usam force.
 */
export function StatusChanger({ application, onChanged }: StatusChangerProps) {
  const { submitting, error, submit } = useSubmit()
  const allowed = application.allowed_next_statuses
  const forced = APPLICATION_STATUSES.filter(
    (status) => status !== application.status && !allowed.includes(status),
  )

  async function handleChange(event: ChangeEvent<HTMLSelectElement>) {
    const next = event.target.value as ApplicationStatus
    if (next === application.status) return
    const needsForce = !allowed.includes(next)
    if (
      needsForce &&
      !window.confirm(
        `Set status to ${labelize(next)}? This bypasses the normal flow and is recorded as a forced change.`,
      )
    ) {
      return
    }
    await submit(() =>
      applicationsApi.changeStatus(application.id, needsForce ? { status: next, force: true } : { status: next }),
    )
    onChanged()
  }

  return (
    <div>
      <select
        aria-label={`Change status of ${application.job.title}`}
        value={application.status}
        disabled={submitting}
        onChange={handleChange}
        className="rounded-md border border-slate-700 bg-slate-950 px-2 py-1 text-sm text-slate-100 focus:outline-none focus:ring-2 focus:ring-sky-500/60 disabled:opacity-50"
      >
        <option value={application.status} disabled>
          {labelize(application.status)} (current)
        </option>
        {allowed.length > 0 ? (
          <optgroup label="Next">
            {allowed.map((status) => (
              <option key={status} value={status}>{labelize(status)}</option>
            ))}
          </optgroup>
        ) : null}
        {forced.length > 0 ? (
          <optgroup label="Correct (forced)">
            {forced.map((status) => (
              <option key={status} value={status}>{labelize(status)}</option>
            ))}
          </optgroup>
        ) : null}
      </select>
      {error ? (
        <p role="alert" className="mt-1 text-xs text-rose-400">
          {describeError(error).message}
        </p>
      ) : null}
    </div>
  )
}
