import { useState } from 'react'
import { Link } from 'react-router-dom'
import { forgotPassword } from '../api/auth'
import { IconMail, IconArrowLeft } from '../components/icons'
import { AuthShell, authButtonCls, authInputCls } from '../components/AuthShell'

function BackToLogin() {
  return (
    <Link
      to="/login"
      className="inline-flex items-center gap-2 font-medium text-muted hover:text-ink"
    >
      <IconArrowLeft className="h-4 w-4" />
      Retour à la connexion
    </Link>
  )
}

export function ForgotPasswordPage() {
  const [email, setEmail] = useState('')
  const [sent, setSent] = useState(false)
  const [submitting, setSubmitting] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setSubmitting(true)
    try {
      await forgotPassword(email)
    } catch {
      // Deliberately swallowed: the endpoint answers 202 whether or not the
      // account exists, and a failure must not reveal anything either. The
      // confirmation shown below is always identical — no account enumeration.
    } finally {
      setSubmitting(false)
      setSent(true)
    }
  }

  if (sent) {
    return (
      <AuthShell
        title="Vérifiez votre boîte mail"
        subtitle="Si un compte est associé à cette adresse, un lien de réinitialisation vient d'être envoyé."
        footer={<BackToLogin />}
      >
        <div className="flex flex-col gap-4">
          <div className="flex items-start gap-3 rounded-xl bg-emerald-50 px-4 py-3.5 text-left">
            <IconMail className="mt-0.5 h-5 w-5 shrink-0 text-emerald-700" />
            <p className="text-sm text-emerald-800">
              Le lien envoyé à <strong className="font-semibold">{email}</strong> expire dans
              30 minutes. Pensez à regarder vos courriers indésirables.
            </p>
          </div>
          <button
            type="button"
            onClick={() => setSent(false)}
            className="text-sm font-medium text-orange hover:underline"
          >
            Utiliser une autre adresse
          </button>
        </div>
      </AuthShell>
    )
  }

  return (
    <AuthShell
      title="Mot de passe oublié ?"
      subtitle="Entrez votre email. Nous vous enverrons un lien de réinitialisation."
      footer={<BackToLogin />}
    >
      <form onSubmit={handleSubmit} className="flex flex-col gap-5 text-left">
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
              autoFocus
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="nom@entreprise.bf"
              className={authInputCls}
            />
          </div>
        </div>

        <button type="submit" disabled={submitting} className={authButtonCls}>
          {submitting ? 'Envoi…' : 'Envoyer le lien de réinitialisation'}
          {!submitting && <span aria-hidden="true">→</span>}
        </button>
      </form>
    </AuthShell>
  )
}
