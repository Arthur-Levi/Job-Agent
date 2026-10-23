import { Navigate, Route, Routes } from 'react-router-dom'
import { ApplicationsPage } from '../pages/ApplicationsPage'
import { DashboardPage } from '../pages/DashboardPage'
import { JobDetailPage } from '../pages/JobDetailPage'
import { JobsPage } from '../pages/JobsPage'
import { NotFoundPage } from '../pages/NotFoundPage'
import { ProfilePage } from '../pages/ProfilePage'
import { AppShell } from './AppShell'

export function App() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="dashboard" element={<DashboardPage />} />
        <Route path="profile" element={<ProfilePage />} />
        <Route path="jobs" element={<JobsPage />} />
        <Route path="jobs/:jobId" element={<JobDetailPage />} />
        <Route path="applications" element={<ApplicationsPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  )
}
