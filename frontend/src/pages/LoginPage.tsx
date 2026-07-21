import { useState } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { useAuth } from '../lib/auth'
import { LogoImage } from '../components/Logo'
import { IconMail } from '../components/icons'
import googleIcon from '../assets/google.svg'

function FeaturePill({ label }: { label: string }) {
  return (
    <span className="inline-flex items-center gap-2 rounded-xl border border-white/10 bg-white/[0.06] px-4 py-2 text-sm text-white/85 backdrop-blur-sm">
      <span className="h-1.5 w-1.5 rounded-full bg-gold" />
      {label}
    </span>
  )
}

export function LoginPage() {
  const { signIn, isAuthenticated } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [remember, setRemember] = useState(true)
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  if (isAuthenticated) return <Navigate to="/" replace />

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      await signIn(email, password, remember)
      navigate('/', { replace: true })
    } catch {
      setError('Email ou mot de passe incorrect.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="flex min-h-screen flex-col lg:flex-row">
      {/* LEFT — brand */}
      <aside className="relative flex w-full flex-col justify-between overflow-hidden bg-navy p-10 lg:w-[42%]">
        <div
          className="pointer-events-none absolute inset-0 opacity-70"
          style={{
            background:
              'radial-gradient(circle at 50% 45%, rgba(201,152,42,0.12) 0%, rgba(201,152,42,0) 55%)',
          }}
        />
        <LogoImage tone="light" className="relative h-24" />

        <div className="relative flex flex-1 items-center justify-center py-10">
          <svg viewBox="0 0 300 280" className="h-64 w-64 opacity-90 lg:h-80 lg:w-80" fill="none">
            <polygon
              points="150,30 260,95 260,215 150,280 40,215 40,95"
              stroke="rgba(201,152,42,0.35)"
              strokeWidth="1.5"
            />
            <g fill="#c9982a">
              {[
                [150, 30],
                [260, 95],
                [260, 215],
                [150, 280],
                [40, 215],
                [40, 95],
                [150, 155],
              ].map(([x, y]) => (
                <circle key={`${x}-${y}`} cx={x} cy={y} r="4" />
              ))}
            </g>
            <g stroke="rgba(201,152,42,0.25)" strokeWidth="1">
              <path d="M150 155 L150 30M150 155 L260 95M150 155 L40 95M150 155 L260 215M150 155 L40 215M150 155 L150 280" />
            </g>
            <rect x="132" y="137" width="36" height="36" rx="6" stroke="rgba(201,152,42,0.6)" strokeWidth="1.5" />
            <path d="M141 150h6M141 156h6M153 150h6M153 156h6" stroke="rgba(201,152,42,0.7)" strokeWidth="1.5" strokeLinecap="round" />
          </svg>
        </div>

        <div className="relative flex flex-wrap gap-3">
          <FeaturePill label="Scraping automatique" />
          <FeaturePill label="Alertes en temps réel" />
          <FeaturePill label="Résumés IA" />
        </div>
      </aside>

      {/* RIGHT — form */}
      <main className="relative flex w-full items-center justify-center bg-white p-8 lg:w-[58%] lg:p-16">
        <div className="w-full max-w-[420px]">
          <p className="text-base text-muted">Bienvenue</p>
          <h1 className="mt-1 font-display text-3xl font-extrabold leading-tight text-ink">
            Connectez-vous à votre espace Tender Monitor
          </h1>

          <button
            type="button"
            disabled
            title="Bientôt disponible"
            className="mt-8 flex w-full cursor-not-allowed items-center justify-center gap-3 rounded-xl border border-line px-6 py-3.5 text-base font-medium text-ink opacity-70"
          >
            <img src={googleIcon} alt="" className="h-5 w-5" />
            Continuer avec Google
          </button>

          <div className="flex items-center py-6">
            <span className="h-px flex-1 bg-line" />
            <span className="px-4 text-xs font-semibold uppercase tracking-widest text-muted-soft">Ou</span>
            <span className="h-px flex-1 bg-line" />
          </div>

          <form onSubmit={handleSubmit} className="flex flex-col gap-5">
            <div className="flex flex-col gap-1.5">
              <label htmlFor="email" className="text-sm font-medium text-ink">
                Adresse Email
              </label>
              <div className="relative">
                <IconMail className="absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-muted-soft" />
                <input
                  id="email"
                  type="email"
                  required
                  autoComplete="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="nom@entreprise.com"
                  className="w-full rounded-xl border border-line py-3.5 pl-12 pr-4 text-base text-ink outline-none placeholder:text-muted-soft focus:border-orange focus:ring-2 focus:ring-orange/15"
                />
              </div>
            </div>

            <div className="flex flex-col gap-1.5">
              <label htmlFor="password" className="text-sm font-medium text-ink">
                Mot de passe
              </label>
              <div className="relative">
                <svg viewBox="0 0 24 24" className="absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-muted-soft" fill="none" stroke="currentColor" strokeWidth="1.8">
                  <rect x="4" y="11" width="16" height="10" rx="2" />
                  <path d="M8 11V7a4 4 0 1 1 8 0v4" />
                </svg>
                <input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  required
                  autoComplete="current-password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full rounded-xl border border-line py-3.5 pl-12 pr-12 text-base text-ink outline-none placeholder:text-muted-soft focus:border-orange focus:ring-2 focus:ring-orange/15"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((v) => !v)}
                  aria-label={showPassword ? 'Masquer le mot de passe' : 'Afficher le mot de passe'}
                  className="absolute right-4 top-1/2 -translate-y-1/2 text-muted-soft hover:text-ink"
                >
                  <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="1.6">
                    <path d="M1 12s4-7 11-7 11 7 11 7-4 7-11 7S1 12 1 12Z" />
                    <circle cx="12" cy="12" r="3" />
                    {!showPassword && <path d="m3 3 18 18" />}
                  </svg>
                </button>
              </div>
            </div>

            <div className="flex items-center justify-between">
              <label className="flex cursor-pointer items-center gap-2 text-sm text-muted">
                <input
                  type="checkbox"
                  checked={remember}
                  onChange={(e) => setRemember(e.target.checked)}
                  className="h-4 w-4 rounded border-line accent-orange"
                />
                Se souvenir de moi
              </label>
              <Link to="/forgot-password" className="text-sm font-medium text-orange hover:underline">
                Mot de passe oublié ?
              </Link>
            </div>

            {error && (
              <p role="alert" className="rounded-lg bg-red-50 px-4 py-2 text-sm text-red-700">
                {error}
              </p>
            )}

            <button
              type="submit"
              disabled={submitting}
              className="w-full rounded-xl bg-orange py-4 text-base font-semibold text-white shadow-lg shadow-orange/20 transition-colors hover:bg-orange-dark disabled:opacity-60"
            >
              {submitting ? 'Connexion…' : 'Se connecter'}
            </button>
          </form>

          <p className="mt-8 text-center text-base text-muted">
            Pas encore de compte ?{' '}
            <Link to="/register" className="font-bold text-ink hover:underline">
              Créer un compte →
            </Link>
          </p>

          <footer className="mt-10 text-center text-xs uppercase tracking-widest text-muted-soft">
            © 2025 Tender Monitor
          </footer>
        </div>
      </main>
    </div>
  )
}
