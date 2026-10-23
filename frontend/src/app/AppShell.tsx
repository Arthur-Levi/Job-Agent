import { NavLink, Outlet, useLocation } from 'react-router-dom'
import { ErrorBoundary } from '../components/ErrorBoundary'

const NAV = [
  { to: '/dashboard', label: 'Dashboard' },
  { to: '/profile', label: 'Profile' },
  { to: '/jobs', label: 'Jobs' },
  { to: '/applications', label: 'Applications' },
]

export function AppShell() {
  const { pathname } = useLocation()
  return (
    <div className="flex min-h-screen flex-col">
      <header className="flex items-center border-b border-slate-800 bg-slate-900/80 px-4 py-3">
        <span className="text-sm font-semibold tracking-[0.25em] text-sky-400">JOB AGENT</span>
        <span className="ml-3 text-xs text-slate-500">local user</span>
      </header>
      <div className="flex flex-1 flex-col md:flex-row">
        <nav aria-label="Main" className="border-b border-slate-800 md:w-52 md:shrink-0 md:border-b-0 md:border-r">
          <ul className="flex gap-1 overflow-x-auto p-2 md:flex-col">
            {NAV.map((item) => (
              <li key={item.to}>
                <NavLink
                  to={item.to}
                  className={({ isActive }) =>
                    `block whitespace-nowrap rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
                      isActive ? 'bg-sky-500/15 text-sky-300' : 'text-slate-400 hover:bg-slate-800 hover:text-slate-200'
                    }`
                  }
                >
                  {item.label}
                </NavLink>
              </li>
            ))}
          </ul>
        </nav>
        <main className="min-w-0 flex-1 p-4 md:p-6">
          <ErrorBoundary key={pathname}>
            <Outlet />
          </ErrorBoundary>
        </main>
      </div>
    </div>
  )
}
