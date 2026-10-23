import type { ReactNode } from 'react'
import { Card } from '../../components/Card'
import type { Profile } from '../../types/api'
import { formatDateTime, labelize } from '../../utils/format'

function Item({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div>
      <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</dt>
      <dd className="mt-0.5 text-sm text-slate-200">{children || '—'}</dd>
    </div>
  )
}

export function ProfileView({ profile }: { profile: Profile }) {
  const location = [profile.city, profile.state, profile.country].filter(Boolean).join(', ')
  return (
    <Card>
      <dl className="grid gap-4 sm:grid-cols-2">
        <div className="sm:col-span-2">
          <Item label="Headline">{profile.headline}</Item>
        </div>
        <div className="sm:col-span-2">
          <Item label="Summary">
            {profile.summary ? <span className="whitespace-pre-wrap">{profile.summary}</span> : null}
          </Item>
        </div>
        <Item label="Location">{location}</Item>
        <Item label="Desired work model">
          {profile.desired_work_model ? labelize(profile.desired_work_model) : null}
        </Item>
        <Item label="Desired seniority">
          {profile.desired_seniority ? labelize(profile.desired_seniority) : null}
        </Item>
        <Item label="Last updated">{formatDateTime(profile.updated_at)}</Item>
      </dl>
    </Card>
  )
}
