import { useState } from 'react'
import type { FormEvent } from 'react'
import { Button } from '../../components/Button'
import { SelectField, TextAreaField, TextField } from '../../components/Field'
import { ErrorBanner } from '../../components/States'
import { useSubmit } from '../../hooks/useSubmit'
import { profileApi } from '../../services/profileApi'
import { SENIORITIES, WORK_MODELS } from '../../types/api'
import type { Profile, Seniority, WorkModel } from '../../types/api'
import { fieldErrorsFrom } from '../../utils/errors'
import { labelize } from '../../utils/format'
import { toProfileInput, toProfileValues } from './profileFormModel'
import type { ProfileFormValues } from './profileFormModel'

const WORK_MODEL_OPTIONS = WORK_MODELS.map((value) => ({ value, label: labelize(value) }))
const SENIORITY_OPTIONS = SENIORITIES.map((value) => ({ value, label: labelize(value) }))

interface ProfileFormProps {
  profile: Profile | null
  onSaved: () => void
  onCancel: () => void
}

export function ProfileForm({ profile, onSaved, onCancel }: ProfileFormProps) {
  const [values, setValues] = useState<ProfileFormValues>(() => toProfileValues(profile))
  const { submitting, error, submit } = useSubmit()
  const serverErrors = fieldErrorsFrom(error)

  function set<K extends keyof ProfileFormValues>(key: K, value: ProfileFormValues[K]) {
    setValues((current) => ({ ...current, [key]: value }))
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    const input = toProfileInput(values)
    const result = await submit(() => (profile ? profileApi.update(input) : profileApi.create(input)))
    if (result.ok) onSaved()
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4" noValidate>
      <TextField
        label="Headline"
        value={values.headline}
        maxLength={200}
        onChange={(e) => set('headline', e.target.value)}
        error={serverErrors.headline}
        placeholder="e.g. Backend developer focused on Python"
      />
      <TextAreaField
        label="Summary"
        rows={5}
        value={values.summary}
        onChange={(e) => set('summary', e.target.value)}
        error={serverErrors.summary}
      />
      <div className="grid gap-4 sm:grid-cols-3">
        <TextField label="City" value={values.city} onChange={(e) => set('city', e.target.value)} error={serverErrors.city} />
        <TextField label="State" value={values.state} onChange={(e) => set('state', e.target.value)} error={serverErrors.state} />
        <TextField label="Country" value={values.country} onChange={(e) => set('country', e.target.value)} error={serverErrors.country} />
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        <SelectField
          label="Desired work model"
          placeholder="No preference"
          options={WORK_MODEL_OPTIONS}
          value={values.desired_work_model}
          onChange={(e) => set('desired_work_model', e.target.value as WorkModel | '')}
          error={serverErrors.desired_work_model}
        />
        <SelectField
          label="Desired seniority"
          placeholder="No preference"
          options={SENIORITY_OPTIONS}
          value={values.desired_seniority}
          onChange={(e) => set('desired_seniority', e.target.value as Seniority | '')}
          error={serverErrors.desired_seniority}
        />
      </div>
      {error && Object.keys(serverErrors).length === 0 ? <ErrorBanner error={error} /> : null}
      <div className="flex gap-2">
        <Button type="submit" disabled={submitting}>
          {submitting ? 'Saving…' : profile ? 'Save changes' : 'Create profile'}
        </Button>
        <Button variant="ghost" onClick={onCancel} disabled={submitting}>
          Cancel
        </Button>
      </div>
    </form>
  )
}
