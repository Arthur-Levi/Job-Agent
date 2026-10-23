import { useState } from 'react'
import type { FormEvent } from 'react'
import { Button } from '../../components/Button'
import { SelectField, TextAreaField, TextField } from '../../components/Field'
import { ErrorBanner } from '../../components/States'
import { useSubmit } from '../../hooks/useSubmit'
import { jobsApi } from '../../services/jobsApi'
import { EMPLOYMENT_TYPES, JOB_STATUSES, SENIORITIES, WORK_MODELS } from '../../types/api'
import type { EmploymentType, Job, JobStatus, Seniority, WorkModel } from '../../types/api'
import { fieldErrorsFrom } from '../../utils/errors'
import { labelize } from '../../utils/format'
import { toJobInput, toJobValues, validateJob } from './jobFormModel'
import type { JobFormValues } from './jobFormModel'

const opts = (values: readonly string[]) => values.map((value) => ({ value, label: labelize(value) }))
const WORK_MODEL_OPTIONS = opts(WORK_MODELS)
const EMPLOYMENT_OPTIONS = opts(EMPLOYMENT_TYPES)
const SENIORITY_OPTIONS = opts(SENIORITIES)
const STATUS_OPTIONS = opts(JOB_STATUSES)

interface JobFormProps {
  job?: Job
  onSaved: (job: Job) => void
  onCancel: () => void
}

export function JobForm({ job, onSaved, onCancel }: JobFormProps) {
  const [values, setValues] = useState<JobFormValues>(() => toJobValues(job))
  const [clientErrors, setClientErrors] = useState<Record<string, string>>({})
  const { submitting, error, submit } = useSubmit()
  const serverErrors = fieldErrorsFrom(error)
  const errorFor = (name: string) => clientErrors[name] ?? serverErrors[name]

  function set<K extends keyof JobFormValues>(key: K, value: JobFormValues[K]) {
    setValues((current) => ({ ...current, [key]: value }))
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    const problems = validateJob(values)
    setClientErrors(problems)
    if (Object.keys(problems).length > 0) return
    const input = toJobInput(values)
    const result = await submit(() => (job ? jobsApi.update(job.id, input) : jobsApi.create(input)))
    if (result.ok) onSaved(result.value)
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4" noValidate aria-label={job ? 'Edit job' : 'Add job'}>
      <div className="grid gap-4 sm:grid-cols-2">
        <TextField label="Title *" value={values.title} maxLength={200} onChange={(e) => set('title', e.target.value)} error={errorFor('title')} />
        <TextField label="Company *" value={values.company} maxLength={200} onChange={(e) => set('company', e.target.value)} error={errorFor('company')} />
      </div>
      <TextAreaField label="Description *" rows={8} value={values.description} onChange={(e) => set('description', e.target.value)} error={errorFor('description')} />
      <div className="grid gap-4 sm:grid-cols-2">
        <TextField label="Location" value={values.location} onChange={(e) => set('location', e.target.value)} error={errorFor('location')} />
        <TextField label="Published on" type="date" value={values.published_at} onChange={(e) => set('published_at', e.target.value)} error={errorFor('published_at')} />
        <TextField label="Source" value={values.source} placeholder="e.g. LinkedIn" onChange={(e) => set('source', e.target.value)} error={errorFor('source')} />
        <TextField label="Source URL" type="url" value={values.source_url} placeholder="https://…" onChange={(e) => set('source_url', e.target.value)} error={errorFor('source_url')} />
      </div>
      <div className="grid gap-4 sm:grid-cols-3">
        <SelectField label="Work model" placeholder="Not specified" options={WORK_MODEL_OPTIONS} value={values.work_model} onChange={(e) => set('work_model', e.target.value as WorkModel | '')} error={errorFor('work_model')} />
        <SelectField label="Employment type" placeholder="Not specified" options={EMPLOYMENT_OPTIONS} value={values.employment_type} onChange={(e) => set('employment_type', e.target.value as EmploymentType | '')} error={errorFor('employment_type')} />
        <SelectField label="Seniority" placeholder="Not specified" options={SENIORITY_OPTIONS} value={values.seniority} onChange={(e) => set('seniority', e.target.value as Seniority | '')} error={errorFor('seniority')} />
      </div>
      <div className="grid gap-4 sm:grid-cols-4">
        <TextField label="Salary min" inputMode="decimal" value={values.salary_min} onChange={(e) => set('salary_min', e.target.value)} error={errorFor('salary_min')} />
        <TextField label="Salary max" inputMode="decimal" value={values.salary_max} onChange={(e) => set('salary_max', e.target.value)} error={errorFor('salary_max')} />
        <TextField label="Currency" maxLength={3} value={values.currency} placeholder="BRL" onChange={(e) => set('currency', e.target.value)} error={errorFor('currency')} />
        <SelectField label="Status" options={STATUS_OPTIONS} value={values.status} onChange={(e) => set('status', e.target.value as JobStatus)} error={errorFor('status')} />
      </div>
      {error && Object.keys(serverErrors).length === 0 ? <ErrorBanner error={error} /> : null}
      <div className="flex gap-2">
        <Button type="submit" disabled={submitting}>
          {submitting ? 'Saving…' : job ? 'Save changes' : 'Add job'}
        </Button>
        <Button variant="ghost" onClick={onCancel} disabled={submitting}>
          Cancel
        </Button>
      </div>
    </form>
  )
}
