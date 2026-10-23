import { useState } from 'react'
import { AsyncView } from '../components/AsyncView'
import { Button } from '../components/Button'
import { Card } from '../components/Card'
import { PageHeader } from '../components/PageHeader'
import { EmptyState } from '../components/States'
import { ProfileForm } from '../features/profile/ProfileForm'
import { ProfileView } from '../features/profile/ProfileView'
import { useApiQuery } from '../hooks/useApiQuery'
import { profileApi } from '../services/profileApi'

const fetchProfile = (signal: AbortSignal) => profileApi.get(signal)

export function ProfilePage() {
  const query = useApiQuery(fetchProfile)
  const [editing, setEditing] = useState(false)

  const done = () => {
    setEditing(false)
    query.reload()
  }

  return (
    <>
      <PageHeader
        title="Profile"
        subtitle="Your candidate profile. It will grow in the next phases."
        actions={
          !editing && query.state.status === 'success' && query.state.data ? (
            <Button variant="secondary" onClick={() => setEditing(true)}>
              Edit profile
            </Button>
          ) : null
        }
      />
      <AsyncView
        query={query}
        loadingLabel="Loading profile…"
        isEmpty={(profile) => profile === null && !editing}
        empty={
          <EmptyState
            title="No profile yet"
            description="Create your profile to describe who you are and what you are looking for."
            action={<Button onClick={() => setEditing(true)}>Create profile</Button>}
          />
        }
      >
        {(profile) =>
          editing ? (
            <Card>
              <ProfileForm profile={profile} onSaved={done} onCancel={() => setEditing(false)} />
            </Card>
          ) : profile ? (
            <ProfileView profile={profile} />
          ) : null
        }
      </AsyncView>
    </>
  )
}
