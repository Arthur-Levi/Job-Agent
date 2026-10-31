import { Navigate, Outlet, Route, Routes, useLocation } from 'react-router-dom'
import { ApplicationsPage } from '../pages/ApplicationsPage'
import { RequestAccountEmailPage, ResetPasswordPage, VerifyEmailPage } from '../pages/AccountRecoveryPages'
import { DashboardPage } from '../pages/DashboardPage'
import { JobDetailPage } from '../pages/JobDetailPage'
import { JobsPage } from '../pages/JobsPage'
import { LoginPage } from '../pages/LoginPage'
import { NotFoundPage } from '../pages/NotFoundPage'
import { ProfilePage } from '../pages/ProfilePage'
import { RegisterPage } from '../pages/RegisterPage'
import { AuthProvider } from './AuthProvider'
import { useAuth } from './authContext'
import { AppShell } from './AppShell'

function ProtectedRoute() {
  const { status } = useAuth()
  const location = useLocation()
  if (status === 'checking') return <main role="status" className="p-6">Verificando sessão…</main>
  if (status === 'guest') return <Navigate to="/login" state={{ from: location.pathname + location.search }} replace />
  return <Outlet />
}

function AppRoutes() {
  return (
    <Routes>
      <Route path="login" element={<LoginPage />} />
      <Route path="register" element={<RegisterPage />} />
      <Route path="request-verification" element={<RequestAccountEmailPage purpose="verify" />} />
      <Route path="verify-email" element={<VerifyEmailPage />} />
      <Route path="request-password-reset" element={<RequestAccountEmailPage purpose="reset" />} />
      <Route path="reset-password" element={<ResetPasswordPage />} />
      <Route element={<ProtectedRoute />}>
        <Route element={<AppShell />}>
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<DashboardPage />} />
          <Route path="profile" element={<ProfilePage />} />
          <Route path="jobs" element={<JobsPage />} />
          <Route path="jobs/:jobId" element={<JobDetailPage />} />
          <Route path="applications" element={<ApplicationsPage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Route>
    </Routes>
  )
}

export function App() {
  return <AuthProvider><AppRoutes /></AuthProvider>
}
