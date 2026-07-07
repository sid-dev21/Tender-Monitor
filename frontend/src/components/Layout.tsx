import { NavLink, Outlet } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { fetchHealth } from '../api/health'

const navItems = [
  { to: '/', label: 'Dashboard', end: true },
  { to: '/tenders', label: 'Tenders' },
  { to: '/sites', label: 'Sources' },
  { to: '/notifications', label: 'Notifications' },
  { to: '/settings', label: 'Settings' },
]

function HealthBadge() {
  const { data, isError, isLoading } = useQuery({
    queryKey: ['health'],
    queryFn: fetchHealth,
  })

  const ok = data?.status === 'ok' && data?.mongo === 'up'
  const color = isLoading ? 'bg-gray-400' : ok ? 'bg-green-500' : 'bg-red-500'
  const label = isLoading
    ? 'Checking API…'
    : isError
      ? 'API offline'
      : ok
        ? 'API connected'
        : 'API degraded'

  return (
    <div className="flex items-center gap-2 text-sm text-gray-600">
      <span className={`h-2.5 w-2.5 rounded-full ${color}`} />
      {label}
    </div>
  )
}

export function Layout() {
  return (
    <div className="flex min-h-screen bg-gray-50 text-gray-900">
      <aside className="flex w-60 flex-col border-r border-gray-200 bg-white">
        <div className="px-6 py-5 text-lg font-semibold text-indigo-600">
          Tender Monitor
        </div>
        <nav className="flex flex-1 flex-col gap-1 px-3">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                `rounded-md px-3 py-2 text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-indigo-50 text-indigo-700'
                    : 'text-gray-600 hover:bg-gray-100'
                }`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="border-t border-gray-200 px-6 py-4">
          <HealthBadge />
        </div>
      </aside>

      <main className="flex-1 overflow-auto p-8">
        <Outlet />
      </main>
    </div>
  )
}
