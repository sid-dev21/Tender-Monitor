import { useState } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { register as apiRegister } from '../api/auth'
import { useAuth } from '../lib/auth'
import { errorMessage } from '../lib/errors'
import { LogoImage } from '../components/Logo'
import { IconMail } from '../components/icons'
import googleIcon from '../assets/google.svg'

/** 0–4 heuristic strength score for the visual meter. */
function strength(pw: string): number {
  let s = 0
  if (pw.length >= 10) s++
  if (pw.length >= 14) s++
  if (/[a-zA-Z]/.test(pw) && /\d/.test(pw)) s++
  if (/[^a-zA-Z0-9]/.test(pw)) s++
  return s
}

const STRENGTH_LABEL = ['Très faible', 'Faible', 'Moyen', 'Bon', 'Excellent']
const STRENGTH_COLOR = ['bg-red-500', 'bg-orange', 'bg-amber-400', 'bg-emerald-400', 'bg-emerald-500']

function PwInput({
  id,
  label,
  value,
  onChange,
}: {
  id: string
  label: string
  value: string
  onChange: (v: string) => void
}) {
  const [show, setShow] = useState(false)
  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={id} className="text-sm font-semibold text-ink">
        {label}
      </label>
      <div className="relative">
        <input
          id={id}
          type={show ? 'text' : 'password'}
          required
          minLength={10}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder="••••••••"
          className="w-full rounded-xl border border-line py-3.5 pl-4 pr-12 text-base text-ink outline-none placeholder:text-muted-soft focus:border-orange focus:ring-2 focus:ring-orange/15"
        />
        <button
          type="button"
          onClick={() => setShow((v) => !v)}
          aria-label={show ? 'Masquer' : 'Afficher'}
          className="absolute right-4 top-1/2 -translate-y-1/2 text-muted-soft hover:text-ink"
        >
          <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="1.6">
            <path d="M1 12s4-7 11-7 11 7 11 7-4 7-11 7S1 12 1 12Z" />
            <circle cx="12" cy="12" r="3" />
            {!show && <path d="m3 3 18 18" />}
          </svg>
        </button>
      </div>
    </div>
  )
}

export function RegisterPage() {
  const { signIn, isAuthenticated } = useAuth()
  const navigate = useNavigate()
  const [first, setFirst] = useState('')
  const [last, setLast] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [accept, setAccept] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  if (isAuthenticated) return <Navigate to="/" replace />

  const score = strength(password)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    if (password !== confirm) {
      setError('Les mots de passe ne correspondent pas.')
      return
    }
    if (!accept) {
      setError("Veuillez accepter les conditions d'utilisation.")
      return
    }
    setSubmitting(true)
    try {
      await apiRegister(email, password)
      await signIn(email, password, true) // auto-login after signup
      navigate('/', { replace: true })
    } catch (err) {
      const status = (err as { response?: { status?: number } })?.response?.status
      const raw = errorMessage(err, '')
      if (status === 422) {
        setError('Mot de passe invalide : au moins 10 caractères, avec des lettres et des chiffres.')
      } else if (status === 400 || status === 409 || /regist|exist|déjà/i.test(raw)) {
        setError('Cet email est déjà utilisé.')
      } else {
        setError('Inscription impossible. Réessayez.')
      }
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="flex min-h-screen flex-col lg:flex-row">
      {/* LEFT — brand statement */}
      <aside className="relative flex w-full flex-col justify-between overflow-hidden bg-navy p-10 lg:w-[42%] lg:p-12">
        <LogoImage tone="light" className="h-24" />
        <div className="max-w-md">
          <h1 className="font-display text-5xl font-extrabold leading-[1.05] text-white">
            L'excellence dans la commande publique.
          </h1>
          <p className="mt-6 text-lg leading-relaxed text-white/70">
            Accédez aux meilleures opportunités de marchés publics grâce à notre plateforme de veille
            intelligente et boostez votre croissance institutionnelle.
          </p>
        </div>
        <p className="text-sm font-semibold uppercase tracking-widest text-white/40">
          Transparence <span className="text-gold">•</span> Excellence <span className="text-gold">•</span> Innovation
        </p>
      </aside>

      {/* RIGHT — form */}
      <main className="flex w-full items-center justify-center bg-white p-8 lg:w-[58%] lg:p-14">
        <div className="w-full max-w-[460px]">
          <h2 className="font-display text-3xl font-extrabold text-ink">Créer un compte</h2>
          <p className="mt-1 text-base text-muted">
            Rejoignez Tender Monitor et commencez à surveiller les marchés
          </p>

          <button
            type="button"
            disabled
            title="Bientôt disponible"
            className="mt-6 flex w-full cursor-not-allowed items-center justify-center gap-3 rounded-xl border border-line px-6 py-3.5 text-base font-medium text-ink opacity-70"
          >
            <img src={googleIcon} alt="" className="h-5 w-5" />
            S'inscrire avec Google
          </button>

          <div className="flex items-center py-5">
            <span className="h-px flex-1 bg-line" />
            <span className="px-3 text-xs font-semibold uppercase tracking-widest text-muted-soft">
              Ou créez un compte manuellement
            </span>
            <span className="h-px flex-1 bg-line" />
          </div>

          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="flex flex-col gap-1.5">
                <label htmlFor="first" className="text-sm font-semibold text-ink">
                  Prénom
                </label>
                <input
                  id="first"
                  value={first}
                  onChange={(e) => setFirst(e.target.value)}
                  placeholder="Boureima"
                  className="rounded-xl border border-line px-4 py-3 text-base text-ink outline-none placeholder:text-muted-soft focus:border-orange focus:ring-2 focus:ring-orange/15"
                />
              </div>
              <div className="flex flex-col gap-1.5">
                <label htmlFor="last" className="text-sm font-semibold text-ink">
                  Nom
                </label>
                <input
                  id="last"
                  value={last}
                  onChange={(e) => setLast(e.target.value)}
                  placeholder="OUEDRAOGO"
                  className="rounded-xl border border-line px-4 py-3 text-base text-ink outline-none placeholder:text-muted-soft focus:border-orange focus:ring-2 focus:ring-orange/15"
                />
              </div>
            </div>

            <div className="flex flex-col gap-1.5">
              <label htmlFor="email" className="text-sm font-semibold text-ink">
                Email professionnel
              </label>
              <div className="relative">
                <IconMail className="absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-muted-soft" />
                <input
                  id="email"
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="nom@entreprise.com"
                  className="w-full rounded-xl border border-line py-3.5 pl-12 pr-4 text-base text-ink outline-none placeholder:text-muted-soft focus:border-orange focus:ring-2 focus:ring-orange/15"
                />
              </div>
            </div>

            <div>
              <PwInput id="password" label="Mot de passe" value={password} onChange={setPassword} />
              {password && (
                <div className="mt-2">
                  <div className="flex gap-1.5">
                    {[0, 1, 2, 3, 4].map((i) => (
                      <span
                        key={i}
                        className={`h-1.5 flex-1 rounded-full ${i < score ? STRENGTH_COLOR[score - 1] : 'bg-line'}`}
                      />
                    ))}
                  </div>
                  <p className="mt-1 text-xs italic text-muted">
                    Force du mot de passe : {STRENGTH_LABEL[score]}
                  </p>
                </div>
              )}
            </div>

            <PwInput id="confirm" label="Confirmer le mot de passe" value={confirm} onChange={setConfirm} />

            <label className="flex cursor-pointer items-start gap-2.5 text-sm text-muted">
              <input
                type="checkbox"
                checked={accept}
                onChange={(e) => setAccept(e.target.checked)}
                className="mt-0.5 h-4 w-4 rounded border-line accent-orange"
              />
              <span>
                J'accepte les <span className="font-semibold text-orange">Conditions d'utilisation</span> et la{' '}
                <span className="font-semibold text-orange">Politique de confidentialité</span> de TenderMonitor.
              </span>
            </label>

            {error && (
              <p role="alert" className="rounded-lg bg-red-50 px-4 py-2 text-sm text-red-700">
                {error}
              </p>
            )}

            <button
              type="submit"
              disabled={submitting}
              className="mt-1 w-full rounded-xl bg-orange py-4 text-base font-semibold text-white shadow-lg shadow-orange/20 transition-colors hover:bg-orange-dark disabled:opacity-60"
            >
              {submitting ? 'Création…' : 'Créer mon compte'}
            </button>
          </form>

          <p className="mt-6 text-center text-base text-muted">
            Déjà un compte ?{' '}
            <Link to="/login" className="font-bold text-ink hover:underline">
              Se connecter →
            </Link>
          </p>
        </div>
      </main>
    </div>
  )
}
