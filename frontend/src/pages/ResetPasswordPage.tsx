import { useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { resetPassword } from '../api/auth'
import { setTokens } from '../lib/tokens'
import { useAuth } from '../lib/auth'
import { errorMessage } from '../lib/errors'
import { IconArrowLeft } from '../components/icons'
import { AuthShell, authButtonCls, authInputCls } from '../components/AuthShell'

/** Mirrors the backend rule (schemas/auth_dto.py): >= 10 chars, letters AND
 * digits. Checked here only to fail fast with a French message; the server
 * remains the authority. */
const MIN_LENGTH = 10

function passwordProblem(value: string): string | null {
  if (value.length < MIN_LENGTH) return `Le mot de passe doit contenir au moins ${MIN_LENGTH} caractères.`
  if (!/\d/.test(value) || !/[a-zA-Z]/.test(value)) {
    return 'Le mot de passe doit contenir des lettres et des chiffres.'
  }
  return null
}

function LockIcon() {
  return (
    <svg
      viewBox="0 0 24 24"
      className="absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-muted-soft"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
    >
      <rect x="4" y="11" width="16" height="10" rx="2" />
      <path d="M8 11V7a4 4 0 1 1 8 0v4" />
    </svg>
  )
}

export function ResetPasswordPage() {
  const [params] = useSearchParams()
  const token = params.get('token') ?? ''
  const navigate = useNavigate()
  const { refreshUser } = useAuth()

  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [show, setShow] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  // A link without a token can only come from a truncated/mangled email —
  // say so plainly rather than failing later with a server error.
  if (!token) {
    return (
      <AuthShell
        title="Lien invalide"
        subtitle="Ce lien de réinitialisation est incomplet ou a été modifié. Demandez-en un nouveau."
        footer={
          <Link to="/login" className="inline-flex items-center gap-2 font-medium text-muted hover:text-ink">
            <IconArrowLeft className="h-4 w-4" />
            Retour à la connexion
          </Link>
        }
      >
        <Link to="/forgot-password" className={authButtonCls}>
          Demander un nouveau lien
        </Link>
      </AuthShell>
    )
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)

    const problem = passwordProblem(password)
    if (problem) return setError(problem)
    if (password !== confirm) return setError('Les deux mots de passe ne correspondent pas.')

    setSubmitting(true)
    try {
      // The endpoint returns a fresh token pair, so a successful reset logs the
      // user straight in — no second trip through the login screen.
      const tokens = await resetPassword(token, password)
      setTokens(tokens.access_token, tokens.refresh_token, false)
      await refreshUser()
      navigate('/', { replace: true })
    } catch (err) {
      setError(
        errorMessage(
          err,
          'Ce lien est invalide ou expiré. Demandez un nouveau lien de réinitialisation.',
        ),
      )
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <AuthShell
      title="Choisissez un nouveau mot de passe"
      subtitle={`Au moins ${MIN_LENGTH} caractères, avec des lettres et des chiffres.`}
      footer={
        <Link to="/login" className="inline-flex items-center gap-2 font-medium text-muted hover:text-ink">
          <IconArrowLeft className="h-4 w-4" />
          Retour à la connexion
        </Link>
      }
    >
      <form onSubmit={handleSubmit} className="flex flex-col gap-5 text-left">
        <div className="flex flex-col gap-1.5">
          <label htmlFor="password" className="text-sm font-semibold text-ink">
            Nouveau mot de passe
          </label>
          <div className="relative">
            <LockIcon />
            <input
              id="password"
              type={show ? 'text' : 'password'}
              required
              autoFocus
              autoComplete="new-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••••"
              className={`${authInputCls} pr-12`}
            />
            <button
              type="button"
              onClick={() => setShow((v) => !v)}
              aria-label={show ? 'Masquer le mot de passe' : 'Afficher le mot de passe'}
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

        <div className="flex flex-col gap-1.5">
          <label htmlFor="confirm" className="text-sm font-semibold text-ink">
            Confirmez le mot de passe
          </label>
          <div className="relative">
            <LockIcon />
            <input
              id="confirm"
              type={show ? 'text' : 'password'}
              required
              autoComplete="new-password"
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              placeholder="••••••••••"
              className={authInputCls}
            />
          </div>
        </div>

        {error && (
          <p role="alert" className="rounded-lg bg-red-50 px-4 py-2 text-sm text-red-700">
            {error}
          </p>
        )}

        <button type="submit" disabled={submitting} className={authButtonCls}>
          {submitting ? 'Enregistrement…' : 'Réinitialiser le mot de passe'}
          {!submitting && <span aria-hidden="true">→</span>}
        </button>
      </form>
    </AuthShell>
  )
}
