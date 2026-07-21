import { useEffect, useState } from 'react'
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { fetchHealth } from '../api/health'
import { useAuth } from '../lib/auth'
import { LogoImage } from './Logo'
import {
  IconDashboard,
  IconTenders,
  IconSources,
  IconAlerts,
  IconSettings,
  IconSearch,
  IconBell,
  IconPlus,
  IconLogout,
} from './icons'
import { displayName, initials } from '../lib/user'

const navItems = [
  { to: '/', label: 'Dashboard', Icon: IconDashboard, end: true },
  { to: '/tenders', label: "Appels d'offres", Icon: IconTenders },
  { to: '/sites', label: 'Sources', Icon: IconSources },
  { to: '/notifications', label: 'Alertes', Icon: IconAlerts },
  { to: '/settings', label: 'Paramètres', Icon: IconSettings },
]

function HealthDot() {
  const { data, isLoading } = useQuery({ queryKey: ['health'], queryFn: fetchHealth })
  const ok = data?.status === 'ok' && data?.mongo === 'up'
  const color = isLoading ? 'bg-white/30' : ok ? 'bg-emerald-400' : 'bg-red-400'
  const label = isLoading ? 'Vérification…' : ok ? 'API connectée' : 'API dégradée'
  return (
    <span className="flex items-center gap-2 text-xs text-white/45">
      <span className={`h-1.5 w-1.5 rounded-full ${color}`} />
      {label}
    </span>
  )
}

function Sidebar({ onNavigate }: { onNavigate?: () => void }) {
  const { signOut } = useAuth()
  const navigate = useNavigate()
  return (
    <div className="flex h-full flex-col bg-sidebar">
      <div className="flex justify-center px-6 py-7">
        <LogoImage tone="light" className="h-24" />
      </div>

      <nav className="flex flex-1 flex-col gap-1 px-3">
        {navItems.map(({ to, label, Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            onClick={onNavigate}
            className={({ isActive }) =>
              `relative flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-sidebar-active text-white'
                  : 'text-white/55 hover:bg-white/5 hover:text-white'
              }`
            }
          >
            {({ isActive }) => (
              <>
                {isActive && (
                  <span className="absolute left-0 top-1/2 h-7 w-1 -translate-y-1/2 rounded-r-full bg-orange" />
                )}
                <Icon className="h-5 w-5" />
                {label}
              </>
            )}
          </NavLink>
        ))}
      </nav>

      <div className="px-4 pb-5">
        <button
          onClick={() => {
            navigate('/sites')
            onNavigate?.()
          }}
          className="flex w-full items-center justify-center gap-2 rounded-xl bg-orange py-3 text-sm font-semibold text-white shadow-lg shadow-orange/25 transition-colors hover:bg-orange-dark"
        >
          <IconPlus className="h-5 w-5" />
          Nouveau Dossier
        </button>
        <div className="mt-4 flex items-center justify-between border-t border-white/10 pt-4">
          <HealthDot />
          <button
            onClick={signOut}
            title="Se déconnecter"
            className="flex items-center gap-1.5 text-xs text-white/45 transition-colors hover:text-white"
          >
            <IconLogout className="h-4 w-4" />
            Quitter
          </button>
        </div>
      </div>
    </div>
  )
}

function IconMenu({ className = 'h-6 w-6' }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.9} strokeLinecap="round" className={className}>
      <path d="M4 7h16M4 12h16M4 17h16" />
    </svg>
  )
}

function TopBar({ onMenu }: { onMenu: () => void }) {
  const { user } = useAuth()
  const navigate = useNavigate()
  const [q, setQ] = useState('')
  return (
    <header className="sticky top-0 z-20 flex h-16 items-center gap-3 border-b border-line bg-bg/85 px-4 backdrop-blur sm:h-20 sm:gap-6 sm:px-8">
      <button
        onClick={onMenu}
        aria-label="Ouvrir le menu"
        className="flex h-10 w-10 items-center justify-center rounded-lg text-ink transition-colors hover:bg-black/[0.04] lg:hidden"
      >
        <IconMenu />
      </button>

      <form
        className="relative hidden max-w-xl flex-1 sm:block"
        onSubmit={(e) => {
          e.preventDefault()
          navigate(q.trim() ? `/tenders?q=${encodeURIComponent(q.trim())}` : '/tenders')
        }}
      >
        <IconSearch className="pointer-events-none absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-muted-soft" />
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Rechercher un appel d'offres, une source…"
          className="w-full rounded-xl border border-line bg-white py-3 pl-12 pr-4 text-sm text-ink outline-none placeholder:text-muted-soft focus:border-orange focus:ring-2 focus:ring-orange/15"
        />
      </form>

      <div className="ml-auto flex items-center gap-3 sm:gap-5">
        <NavLink
          to="/tenders"
          className="flex h-10 w-10 items-center justify-center rounded-lg text-muted transition-colors hover:bg-black/[0.04] hover:text-ink sm:hidden"
          aria-label="Rechercher"
        >
          <IconSearch className="h-5 w-5" />
        </NavLink>
        <NavLink to="/notifications" className="relative text-muted transition-colors hover:text-ink">
          <IconBell className="h-6 w-6" />
          <span className="absolute -right-0.5 -top-0.5 h-2.5 w-2.5 rounded-full border-2 border-bg bg-orange" />
        </NavLink>
        <span className="hidden h-8 w-px bg-line sm:block" />
        <button
          onClick={() => navigate('/profile')}
          className="flex items-center gap-3 rounded-lg py-1 pl-1 pr-1.5 text-left transition-colors hover:bg-black/[0.03]"
        >
          <div className="hidden text-right leading-tight sm:block">
            <p className="text-sm font-semibold text-ink">{displayName(user?.email)}</p>
            <p className="text-xs text-muted-soft">Veille marchés publics</p>
          </div>
          <span className="flex h-10 w-10 items-center justify-center rounded-full bg-navy text-sm font-bold text-gold">
            {initials(displayName(user?.email))}
          </span>
        </button>
      </div>
    </header>
  )
}

export function Layout() {
  const [drawerOpen, setDrawerOpen] = useState(false)
  const location = useLocation()

  // Close the mobile drawer whenever the route changes.
  useEffect(() => {
    setDrawerOpen(false)
  }, [location.pathname])

  return (
    <div className="min-h-screen bg-bg text-ink">
      {/* Desktop sidebar — fixed rail. */}
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-64 lg:block">
        <Sidebar />
      </aside>

      {/* Mobile drawer + backdrop. */}
      {drawerOpen && (
        <div className="fixed inset-0 z-40 lg:hidden">
          <div
            className="absolute inset-0 bg-navy/50 backdrop-blur-sm"
            onClick={() => setDrawerOpen(false)}
          />
          <aside className="absolute inset-y-0 left-0 w-64 shadow-2xl">
            <Sidebar onNavigate={() => setDrawerOpen(false)} />
          </aside>
        </div>
      )}

      <div className="lg:pl-64">
        <TopBar onMenu={() => setDrawerOpen(true)} />
        <main className="px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
