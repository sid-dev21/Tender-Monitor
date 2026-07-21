import { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useAuth } from '../lib/auth'
import { updateKeywords, updateNotificationEmails, updateCompanyProfile } from '../api/users'
import { getSchedule, setSchedule } from '../api/notifications'
import { errorMessage } from '../lib/errors'
import { IconTenders, IconMail, IconCalendar, IconBell, IconUser, IconPlus, IconTrash, IconWarning, IconLightbulb } from '../components/icons'

function Card({
  title,
  description,
  Icon,
  children,
  aside,
}: {
  title: string
  description: string
  Icon: (p: { className?: string }) => React.ReactElement
  children: React.ReactNode
  aside?: React.ReactNode
}) {
  return (
    <section className="rounded-2xl border border-line bg-white p-6 shadow-sm">
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-start gap-3">
          <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-navy/5 text-navy">
            <Icon className="h-5 w-5" />
          </span>
          <div>
            <h2 className="font-display text-lg font-bold text-ink">{title}</h2>
            <p className="mt-0.5 text-sm text-muted">{description}</p>
          </div>
        </div>
        {aside}
      </div>
      <div className="mt-5">{children}</div>
    </section>
  )
}

export function SettingsPage() {
  const { user, refreshUser } = useAuth()
  const { data: schedule } = useQuery({ queryKey: ['schedule'], queryFn: getSchedule })

  const [keywords, setKeywords] = useState<string[]>([])
  const [companyProfile, setCompanyProfile] = useState('')
  const [emails, setEmails] = useState<string[]>([])
  const [kwDraft, setKwDraft] = useState('')
  const [emailDraft, setEmailDraft] = useState('')
  const [frequency, setFrequency] = useState<'daily' | 'weekly'>('daily')
  const [time, setTime] = useState('08:00')
  const [inApp, setInApp] = useState(true)
  const [status, setStatus] = useState<{ kind: 'ok' | 'error'; msg: string } | null>(null)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (user) {
      setKeywords(user.keywords)
      setCompanyProfile(user.company_profile ?? '')
      setEmails(user.notification_emails)
      setInApp(user.in_app_notifications_enabled)
    }
  }, [user])

  useEffect(() => {
    if (schedule) {
      setFrequency(schedule.frequency)
      setTime(schedule.time)
    }
  }, [schedule])

  const KW_MAX = 50
  const EMAIL_MAX = 5

  function addKeyword() {
    const v = kwDraft.trim().toLowerCase()
    if (!v || keywords.includes(v) || keywords.length >= KW_MAX) return
    setKeywords([...keywords, v])
    setKwDraft('')
  }
  function addEmail() {
    const v = emailDraft.trim()
    if (!v || emails.includes(v) || emails.length >= EMAIL_MAX) return
    setEmails([...emails, v])
    setEmailDraft('')
  }

  async function save() {
    setSaving(true)
    setStatus(null)
    try {
      await updateKeywords(keywords)
      await updateCompanyProfile(companyProfile)
      await updateNotificationEmails(emails)
      await setSchedule({ frequency, time, timezone: 'Africa/Ouagadougou' })
      await refreshUser()
      setStatus({ kind: 'ok', msg: 'Modifications enregistrées.' })
    } catch (err) {
      setStatus({ kind: 'error', msg: errorMessage(err, "Échec de l'enregistrement.") })
    } finally {
      setSaving(false)
    }
  }

  function reset() {
    if (user) {
      setKeywords(user.keywords)
      setCompanyProfile(user.company_profile ?? '')
      setEmails(user.notification_emails)
      setInApp(user.in_app_notifications_enabled)
    }
    if (schedule) {
      setFrequency(schedule.frequency)
      setTime(schedule.time)
    }
    setStatus(null)
  }

  return (
    <div className="mx-auto max-w-3xl">
      <h1 className="font-display text-3xl font-extrabold text-ink">Paramètres</h1>
      <p className="mt-1 text-sm text-muted">Réglez ce que vous surveillez et comment vous êtes prévenu.</p>

      <div className="mt-6 flex flex-col gap-6">
        {/* company profile — context for LLM relevance scoring */}
        <Card
          title="Profil de l'entreprise"
          description="Décrivez votre activité : l'IA s'en sert pour noter la pertinence de chaque appel d'offres."
          Icon={IconLightbulb}
        >
          <textarea
            value={companyProfile}
            onChange={(e) => setCompanyProfile(e.target.value.slice(0, 2000))}
            rows={4}
            placeholder="Ex. : Entreprise de BTP basée à Ouagadougou, spécialisée dans les travaux de voirie, l'assainissement et les bâtiments scolaires. Capacité : chantiers jusqu'à 500M FCFA."
            className="w-full rounded-lg border border-line px-3 py-2.5 text-sm outline-none focus:border-orange focus:ring-2 focus:ring-orange/15"
          />
          <p className="mt-2 text-right text-xs font-semibold text-muted-soft">{companyProfile.length} / 2000</p>
        </Card>

        {/* keywords */}
        <Card
          title="Mots-clés de veille"
          description="Les appels d'offres contenant l'un de ces mots vous sont proposés."
          Icon={IconTenders}
        >
          <div className="flex flex-wrap items-center gap-2">
            {keywords.map((k) => (
              <span key={k} className="inline-flex items-center gap-1.5 rounded-full bg-gray-100 px-3 py-1.5 text-sm text-ink">
                {k}
                <button onClick={() => setKeywords(keywords.filter((x) => x !== k))} className="text-muted-soft hover:text-red-600" aria-label={`Retirer ${k}`}>
                  ✕
                </button>
              </span>
            ))}
            {keywords.length < KW_MAX && (
              <input
                value={kwDraft}
                onChange={(e) => setKwDraft(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), addKeyword())}
                placeholder="+ Ajouter"
                className="rounded-full border border-dashed border-orange/60 px-3 py-1.5 text-sm text-orange outline-none placeholder:text-orange focus:border-orange focus:ring-2 focus:ring-orange/15"
              />
            )}
          </div>
          <div className="mt-4 flex items-center justify-between border-t border-line pt-3">
            <p className="flex items-center gap-2 text-xs text-muted">
              <IconWarning className="h-4 w-4 text-muted-soft" />
              Les accents et la casse sont ignorés : <em>école</em>, <em>ECOLE</em> et <em>ecole</em> donnent le même résultat.
            </p>
            <span className="text-xs font-semibold text-muted-soft">{keywords.length} / {KW_MAX}</span>
          </div>
        </Card>

        {/* recipients */}
        <Card
          title="Destinataires des rapports"
          description="Jusqu'à cinq adresses reçoivent le rapport."
          Icon={IconMail}
        >
          <div className="flex flex-col gap-2">
            {emails.map((e) => (
              <div key={e} className="flex items-center justify-between rounded-lg border border-line px-3 py-2.5">
                <span className="flex items-center gap-2 text-sm text-ink">
                  <IconMail className="h-4 w-4 text-muted-soft" />
                  {e}
                </span>
                <button onClick={() => setEmails(emails.filter((x) => x !== e))} className="text-muted-soft hover:text-red-600" aria-label={`Retirer ${e}`}>
                  <IconTrash className="h-4 w-4" />
                </button>
              </div>
            ))}
            {emails.length < EMAIL_MAX && (
              <div className="flex gap-2">
                <input
                  type="email"
                  value={emailDraft}
                  onChange={(e) => setEmailDraft(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), addEmail())}
                  placeholder="nom@entreprise.com"
                  className="flex-1 rounded-lg border border-line px-3 py-2.5 text-base outline-none focus:border-orange focus:ring-2 focus:ring-orange/15"
                />
                <button onClick={addEmail} className="flex items-center gap-1.5 rounded-lg border border-orange px-4 text-sm font-semibold text-orange hover:bg-orange/5">
                  <IconPlus className="h-4 w-4" />
                  Ajouter
                </button>
              </div>
            )}
          </div>
          <p className="mt-3 text-right text-xs font-semibold text-muted-soft">{emails.length} / {EMAIL_MAX}</p>
        </Card>

        {/* frequency */}
        <Card title="Fréquence des rapports" description="Choisissez quand le rapport part." Icon={IconCalendar}>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-muted-soft">Fréquence</p>
              <div className="mt-2 flex overflow-hidden rounded-lg border border-line">
                {([
                  { v: 'daily', label: 'Quotidien' },
                  { v: 'weekly', label: 'Hebdomadaire' },
                ] as const).map((opt) => (
                  <button
                    key={opt.v}
                    onClick={() => setFrequency(opt.v)}
                    className={`flex-1 px-3 py-2.5 text-sm font-semibold ${frequency === opt.v ? 'bg-navy text-white' : 'bg-white text-muted hover:bg-gray-50'}`}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>
            </div>
            <label className="flex flex-col">
              <span className="text-xs font-semibold uppercase tracking-wide text-muted-soft">Heure d'envoi</span>
              <input type="time" value={time} onChange={(e) => setTime(e.target.value)} className="mt-2 rounded-lg border border-line px-3 py-2.5 text-base outline-none focus:border-orange focus:ring-2 focus:ring-orange/15" />
            </label>
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-muted-soft">Fuseau horaire</p>
              <div className="mt-2 rounded-lg border border-line bg-gray-50 px-3 py-2.5 text-sm text-muted">Africa/Ouagadougou (GMT+0)</div>
            </div>
          </div>
          {schedule?.last_sent_at && (
            <p className="mt-4 text-sm text-muted">
              Dernier rapport envoyé le {new Date(schedule.last_sent_at).toLocaleDateString('fr-FR')}.
            </p>
          )}
        </Card>

        {/* notifications */}
        <Card title="Notifications" description="Prévenez-moi aussi dans l'application." Icon={IconBell}>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-semibold text-ink">Notifications dans l'application</p>
              <p className="text-sm text-muted">Un rappel apparaît dans votre boîte de réception à chaque nouveau rapport.</p>
            </div>
            <button
              onClick={() => setInApp((v) => !v)}
              className={`relative h-6 w-11 shrink-0 rounded-full transition-colors ${inApp ? 'bg-orange' : 'bg-line'}`}
              title={inApp ? 'Activées' : 'Désactivées'}
            >
              <span className={`absolute top-0.5 h-5 w-5 rounded-full bg-white transition-all ${inApp ? 'left-[22px]' : 'left-0.5'}`} />
            </button>
          </div>
        </Card>

        {/* account */}
        <Card title="Compte" description="Vos identifiants de connexion." Icon={IconUser}>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-muted-soft">Adresse de connexion</p>
              <p className="mt-1 font-medium text-ink">{user?.email}</p>
            </div>
            <span className="rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-700">
              {user?.is_active ? 'Compte actif' : 'Compte inactif'}
            </span>
          </div>
        </Card>

        {status && (
          <p className={`rounded-lg px-4 py-2 text-sm ${status.kind === 'ok' ? 'bg-emerald-50 text-emerald-700' : 'bg-red-50 text-red-700'}`}>
            {status.msg}
          </p>
        )}

        <div className="flex items-center justify-end gap-3 pb-4">
          <button onClick={reset} className="rounded-xl px-5 py-3 text-sm font-semibold text-muted hover:bg-gray-100">
            Annuler
          </button>
          <button
            onClick={save}
            disabled={saving}
            className="rounded-xl bg-orange px-6 py-3 text-sm font-semibold text-white hover:bg-orange-dark disabled:opacity-60"
          >
            {saving ? 'Enregistrement…' : 'Enregistrer les modifications'}
          </button>
        </div>
      </div>
    </div>
  )
}
