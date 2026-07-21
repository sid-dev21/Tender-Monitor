import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../lib/auth'
import { IconArrowLeft, IconCamera, IconMonitor, IconCalendar } from '../components/icons'
import { displayName, initials } from '../lib/user'

interface ProfileDraft {
  first: string
  last: string
  organisation: string
  role: string
  region: string
  language: 'fr' | 'en'
}

const ROLES = ['Directeur Marchés', 'Responsable Achats', 'Chargé de veille', 'Consultant', 'Autre']
const REGIONS = [
  'Centre (Ouagadougou)',
  'Hauts-Bassins (Bobo-Dioulasso)',
  'Centre-Ouest (Koudougou)',
  'Cascades (Banfora)',
  'Autre',
]

function currentSession(): { browser: string; os: string } {
  const ua = navigator.userAgent
  const browser = /Edg/.test(ua) ? 'Edge' : /Chrome/.test(ua) ? 'Chrome' : /Firefox/.test(ua) ? 'Firefox' : /Safari/.test(ua) ? 'Safari' : 'Navigateur'
  const os = /Windows/.test(ua) ? 'Windows' : /Mac/.test(ua) ? 'macOS' : /Android/.test(ua) ? 'Android' : /Linux/.test(ua) ? 'Linux' : 'Système'
  return { browser, os }
}

const inputCls =
  'rounded-lg border border-line bg-gray-50 px-4 py-3 text-base text-ink outline-none focus:border-orange focus:bg-white focus:ring-2 focus:ring-orange/15'

export function ProfilePage() {
  const { user, signOut } = useAuth()
  const navigate = useNavigate()
  const name = displayName(user?.email)
  const storageKey = `tm.profile.${user?.email ?? 'anon'}`

  const [draft, setDraft] = useState<ProfileDraft>(() => {
    const parts = name.split(' ')
    return {
      first: parts[0] ?? '',
      last: parts.slice(1).join(' '),
      organisation: '',
      role: ROLES[0],
      region: REGIONS[0],
      language: 'fr',
    }
  })
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    const raw = localStorage.getItem(storageKey)
    if (raw) {
      try {
        setDraft((d) => ({ ...d, ...(JSON.parse(raw) as Partial<ProfileDraft>) }))
      } catch {
        /* ignore corrupt cache */
      }
    }
  }, [storageKey])

  function save() {
    localStorage.setItem(storageKey, JSON.stringify(draft))
    setSaved(true)
    setTimeout(() => setSaved(false), 2500)
  }

  const session = currentSession()

  return (
    <div className="mx-auto max-w-4xl">
      <button onClick={() => navigate(-1)} className="flex items-center gap-2 text-sm font-medium text-muted hover:text-ink">
        <IconArrowLeft className="h-4 w-4" />
        Retour
      </button>

      {/* header card */}
      <div className="mt-4 rounded-2xl border border-line bg-white p-6 shadow-sm">
        <div className="flex flex-wrap items-center gap-6">
          <div className="relative">
            <div className="flex h-24 w-24 items-center justify-center rounded-2xl bg-navy/5 font-display text-3xl font-extrabold text-navy">
              {initials(name)}
            </div>
            <button className="absolute -bottom-2 left-1/2 flex h-8 w-8 -translate-x-1/2 items-center justify-center rounded-full border border-line bg-white text-muted shadow-sm hover:text-ink" title="Modifier la photo">
              <IconCamera className="h-4 w-4" />
            </button>
          </div>

          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-3">
              <h1 className="font-display text-2xl font-extrabold text-ink">{name}</h1>
              <span className="rounded-full bg-gold/15 px-3 py-1 text-xs font-bold uppercase tracking-wide text-gold">
                Compte professionnel
              </span>
            </div>
            <p className="mt-1 text-sm text-muted">
              {draft.role}
              {draft.organisation && ` chez ${draft.organisation}`}
            </p>
            <p className="mt-2 text-sm text-muted">{user?.email}</p>
          </div>
        </div>
      </div>

      {/* professional info */}
      <div className="mt-6 rounded-2xl border border-line bg-white p-6 shadow-sm">
        <h2 className="font-display text-lg font-bold text-ink">Informations professionnelles</h2>
        <p className="mt-1 text-sm text-muted">Enregistrées sur cet appareil (le backend ne stocke pas encore ces champs).</p>

        <div className="mt-6 grid grid-cols-1 gap-5 sm:grid-cols-2">
          <label className="flex flex-col gap-1.5">
            <span className="text-sm font-semibold text-ink">Prénom</span>
            <input value={draft.first} onChange={(e) => setDraft({ ...draft, first: e.target.value })} className={inputCls} />
          </label>
          <label className="flex flex-col gap-1.5">
            <span className="text-sm font-semibold text-ink">Nom</span>
            <input value={draft.last} onChange={(e) => setDraft({ ...draft, last: e.target.value })} className={inputCls} />
          </label>
          <label className="flex flex-col gap-1.5 sm:col-span-2">
            <span className="text-sm font-semibold text-ink">Organisation</span>
            <input value={draft.organisation} onChange={(e) => setDraft({ ...draft, organisation: e.target.value })} placeholder="ex. Direction Générale des Marchés Publics" className={inputCls} />
          </label>
          <label className="flex flex-col gap-1.5">
            <span className="text-sm font-semibold text-ink">Rôle</span>
            <select value={draft.role} onChange={(e) => setDraft({ ...draft, role: e.target.value })} className={inputCls}>
              {ROLES.map((r) => (
                <option key={r}>{r}</option>
              ))}
            </select>
          </label>
          <label className="flex flex-col gap-1.5">
            <span className="text-sm font-semibold text-ink">Région (Burkina Faso)</span>
            <select value={draft.region} onChange={(e) => setDraft({ ...draft, region: e.target.value })} className={inputCls}>
              {REGIONS.map((r) => (
                <option key={r}>{r}</option>
              ))}
            </select>
          </label>
        </div>

        <div className="mt-6 border-t border-line pt-6">
          <p className="text-sm font-semibold text-ink">Langue de l'interface</p>
          <div className="mt-3 grid grid-cols-2 gap-3">
            {([
              { v: 'fr', label: 'Français' },
              { v: 'en', label: 'English' },
            ] as const).map((opt) => (
              <button
                key={opt.v}
                onClick={() => setDraft({ ...draft, language: opt.v })}
                className={`rounded-xl border py-3 text-sm font-semibold ${
                  draft.language === opt.v ? 'border-navy bg-gray-50 text-ink' : 'border-line text-muted hover:bg-gray-50'
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>

        <div className="mt-6 flex items-center justify-end gap-3">
          {saved && <span className="text-sm text-emerald-600">Enregistré ✓</span>}
          <button onClick={save} className="rounded-xl bg-orange px-6 py-3 text-sm font-semibold text-white hover:bg-orange-dark">
            Enregistrer les modifications
          </button>
        </div>
      </div>

      {/* recent activity */}
      <div className="mt-6 rounded-2xl border border-line bg-white p-6 shadow-sm">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="font-display text-lg font-bold text-ink">Activité récente</h2>
            <p className="mt-0.5 text-sm text-muted">Sessions de connexion actives.</p>
          </div>
          <button onClick={signOut} className="rounded-xl border border-red-200 px-4 py-2 text-sm font-semibold text-red-600 hover:bg-red-50">
            Déconnecter tous les appareils
          </button>
        </div>

        <div className="mt-5 flex items-center justify-between border-t border-line pt-5">
          <div className="flex items-center gap-3">
            <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-navy/5 text-navy">
              <IconMonitor className="h-5 w-5" />
            </span>
            <div>
              <p className="flex items-center gap-2 text-sm font-semibold text-ink">
                {session.browser} sur {session.os}
                <span className="rounded bg-emerald-50 px-2 py-0.5 text-[11px] font-bold uppercase text-emerald-700">Session actuelle</span>
              </p>
              <p className="text-xs text-muted-soft">Cet appareil</p>
            </div>
          </div>
          <span className="flex items-center gap-1.5 text-sm text-muted">
            <IconCalendar className="h-4 w-4 text-muted-soft" />
            Aujourd'hui
          </span>
        </div>
      </div>
    </div>
  )
}
