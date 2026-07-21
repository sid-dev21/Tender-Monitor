import { useState } from 'react'
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { listTenders } from '../api/tenders'
import type { Tender } from '../api/tenders'
import {
  IconSources,
  IconFile,
  IconDownload,
  IconShare,
  IconStar,
  IconLightbulb,
  IconBell,
  IconChevronRight,
} from '../components/icons'
import { fmtDate, fmtMoney, daysLeft } from '../lib/format'

function completeness(t: Tender): number {
  const fields = [
    t.reference_number,
    t.deadline,
    t.estimated_budget,
    t.contracting_authority,
    t.publication_date,
    t.document_url,
  ]
  return Math.round((fields.filter((f) => f != null && f !== '').length / fields.length) * 100)
}

function KeyInfo({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="border-b border-line py-4 last:border-0">
      <p className="text-xs font-medium uppercase tracking-wide text-muted-soft">{label}</p>
      <div className="mt-1 font-display text-base font-bold text-ink">{children}</div>
    </div>
  )
}

export function TenderDetailPage() {
  const { id } = useParams()
  const location = useLocation()
  const navigate = useNavigate()
  const [starred, setStarred] = useState(false)

  const fromState = (location.state as { tender?: Tender } | null)?.tender
  const { data: list } = useQuery({
    queryKey: ['tenders', ''],
    queryFn: () => listTenders(),
    enabled: !fromState,
  })
  const tender = fromState ?? list?.find((t) => t.id === id)

  if (!tender) {
    return (
      <div className="rounded-2xl border border-dashed border-line bg-white p-12 text-center text-muted">
        Appel d'offres introuvable.{' '}
        <Link to="/tenders" className="font-semibold text-orange hover:underline">
          Retour à la liste
        </Link>
      </div>
    )
  }

  const d = daysLeft(tender.deadline)
  const expired = d != null && d < 0
  const pct = completeness(tender)
  const similar = (list ?? []).filter(
    (t) => t.id !== tender.id && t.matched_keywords.some((k) => tender.matched_keywords.includes(k)),
  ).slice(0, 2)

  return (
    <div className="pb-24">
      {/* breadcrumb */}
      <nav className="flex items-center gap-2 text-sm text-muted">
        <Link to="/" className="hover:text-orange">Tableau de bord</Link>
        <IconChevronRight className="h-4 w-4 text-muted-soft" />
        <Link to="/tenders" className="hover:text-orange">Appels d'offres</Link>
        <IconChevronRight className="h-4 w-4 text-muted-soft" />
        <span className="truncate font-medium text-ink">{tender.title}</span>
      </nav>

      <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* main column */}
        <div className="flex flex-col gap-6 lg:col-span-2">
          {/* title card */}
          <div className="rounded-2xl border border-line bg-white p-6 shadow-sm">
            <div className="flex flex-wrap items-start justify-between gap-3">
              {tender.contracting_authority && (
                <span className="inline-flex items-center gap-2 rounded-lg bg-navy/5 px-3 py-1.5 text-xs font-bold uppercase tracking-wide text-navy">
                  <IconSources className="h-4 w-4" />
                  {tender.contracting_authority}
                </span>
              )}
              <div className="flex items-center gap-2">
                <span
                  className={`rounded-md px-2.5 py-1 text-xs font-bold uppercase ${
                    expired ? 'bg-gray-100 text-muted' : 'bg-emerald-50 text-emerald-700'
                  }`}
                >
                  {expired ? 'Clôturé' : 'Ouvert'}
                </span>
                {d != null && (
                  <span className={`rounded-md px-2.5 py-1 text-xs font-bold ${expired ? 'bg-gray-100 text-muted' : 'bg-red-50 text-red-600'}`}>
                    {expired ? `J+${Math.abs(d)}` : `J-${d}`}
                  </span>
                )}
              </div>
            </div>

            <h1 className="mt-4 font-display text-2xl font-extrabold leading-tight text-ink">{tender.title}</h1>
            {tender.contracting_authority && (
              <p className="mt-3 flex items-center gap-2 text-sm font-medium text-muted">
                <IconSources className="h-4 w-4 text-muted-soft" />
                {tender.contracting_authority}
              </p>
            )}
          </div>

          {/* synthesis (auto-generated from extracted fields — not an LLM claim) */}
          <div className="rounded-2xl border border-violet-100 bg-gradient-to-br from-violet-50 to-white p-6">
            <div className="flex items-center gap-2 text-orange">
              <IconLightbulb className="h-5 w-5" />
              <h2 className="font-display text-sm font-extrabold uppercase tracking-wide">Synthèse Tender Monitor</h2>
            </div>
            <ul className="mt-4 flex flex-col gap-3 text-sm text-ink">
              <li className="flex gap-2">
                <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-orange" />
                <span>
                  <span className="font-bold">Budget :</span>{' '}
                  {tender.estimated_budget != null
                    ? `${fmtMoney(tender.estimated_budget, tender.currency)} estimés.`
                    : 'non extrait du document source.'}
                </span>
              </li>
              <li className="flex gap-2">
                <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-orange" />
                <span>
                  <span className="font-bold">Échéance :</span>{' '}
                  {tender.deadline
                    ? expired
                      ? `clôturé le ${fmtDate(tender.deadline)}.`
                      : `réponse attendue avant le ${fmtDate(tender.deadline)} (${d} jours).`
                    : 'aucune date limite détectée.'}
                </span>
              </li>
              <li className="flex gap-2">
                <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-orange" />
                <span>
                  <span className="font-bold">Pertinence :</span>{' '}
                  {tender.matched_keywords.length > 0
                    ? `correspond à vos mots-clés ${tender.matched_keywords.join(', ')}.`
                    : 'aucun mot-clé de veille ne correspond.'}
                </span>
              </li>
            </ul>
          </div>

          {/* description + similar */}
          <div className="rounded-2xl border border-line bg-white p-6 shadow-sm">
            <div className="flex items-center gap-2">
              <IconFile className="h-5 w-5 text-navy" />
              <h2 className="font-display text-lg font-bold text-ink">Description du projet</h2>
            </div>
            <p className="mt-4 text-sm leading-relaxed text-muted">
              Le détail complet de cet appel d'offres (cahier des charges, lots techniques, critères) figure dans
              le document source publié par {tender.contracting_authority ?? "l'autorité contractante"}. Ouvrez le
              dossier pour consulter les pièces originales.
            </p>

            {similar.length > 0 && (
              <>
                <h3 className="mt-6 text-xs font-bold uppercase tracking-wide text-muted-soft">
                  Appels d'offres similaires
                </h3>
                <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2">
                  {similar.map((s) => {
                    const sd = daysLeft(s.deadline)
                    return (
                      <Link
                        key={s.id}
                        to={`/tenders/${s.id}`}
                        state={{ tender: s }}
                        className="rounded-xl border border-line p-4 transition-colors hover:border-orange/40"
                      >
                        {s.contracting_authority && (
                          <p className="text-[11px] font-bold uppercase text-muted-soft">{s.contracting_authority}</p>
                        )}
                        <p className="mt-1 line-clamp-2 text-sm font-bold text-ink">{s.title}</p>
                        <div className="mt-2 flex items-center justify-between text-xs">
                          <span className="text-muted">{fmtMoney(s.estimated_budget, s.currency)}</span>
                          {sd != null && (
                            <span className={sd < 0 ? 'text-muted' : sd <= 7 ? 'text-red-600' : 'text-emerald-600'}>
                              {sd < 0 ? 'Expiré' : `J-${sd}`}
                            </span>
                          )}
                        </div>
                      </Link>
                    )
                  })}
                </div>
              </>
            )}
          </div>
        </div>

        {/* sidebar */}
        <div className="flex flex-col gap-6">
          <div className="rounded-2xl border border-line bg-white p-6 shadow-sm">
            <h2 className="text-sm font-extrabold uppercase tracking-wide text-ink">Informations clés</h2>
            <div className="mt-2">
              <KeyInfo label="Référence marché">{tender.reference_number || '—'}</KeyInfo>
              <KeyInfo label="Budget estimé">{fmtMoney(tender.estimated_budget, tender.currency)}</KeyInfo>
              <KeyInfo label="Date de publication">{fmtDate(tender.publication_date)}</KeyInfo>
              <KeyInfo label="Date limite de réponse">
                <span className={expired ? 'text-muted' : 'text-red-600'}>{fmtDate(tender.deadline)}</span>
              </KeyInfo>
              <div className="py-4">
                <p className="text-xs font-medium uppercase tracking-wide text-muted-soft">
                  Taux de complétude du dossier
                </p>
                <div className="mt-2 h-2 overflow-hidden rounded-full bg-line">
                  <div
                    className={`h-full rounded-full ${pct >= 66 ? 'bg-emerald-500' : pct >= 33 ? 'bg-amber-400' : 'bg-red-500'}`}
                    style={{ width: `${pct}%` }}
                  />
                </div>
                <p className={`mt-1.5 text-xs font-bold ${pct >= 66 ? 'text-emerald-600' : 'text-amber-600'}`}>
                  {pct}% — {pct >= 66 ? 'Élevé' : pct >= 33 ? 'Moyen' : 'Faible'}
                </p>
              </div>
            </div>
          </div>

          <div className="rounded-2xl border border-line bg-white p-6 shadow-sm">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-extrabold uppercase tracking-wide text-ink">Dossier</h2>
              <span className="text-xs text-muted-soft">{tender.document_url ? '1 fichier' : '0 fichier'}</span>
            </div>
            {tender.document_url ? (
              <a
                href={tender.document_url}
                target="_blank"
                rel="noreferrer"
                className="mt-4 flex items-center gap-3 rounded-xl border border-line p-3 transition-colors hover:border-orange/40"
              >
                <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-red-50 text-red-500">
                  <IconFile className="h-5 w-5" />
                </span>
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-sm font-semibold text-ink">Document source</span>
                  <span className="block text-xs text-muted-soft">Ouvrir dans un nouvel onglet</span>
                </span>
                <IconDownload className="h-4 w-4 text-muted-soft" />
              </a>
            ) : (
              <p className="mt-4 text-sm text-muted">Aucun document attaché à cet appel d'offres.</p>
            )}
          </div>
        </div>
      </div>

      {/* action bar — full width on mobile, offset by the sidebar rail from lg up */}
      <div className="fixed bottom-0 left-0 right-0 z-20 flex items-center justify-between gap-3 border-t border-line bg-white/90 px-4 py-3 backdrop-blur sm:px-6 lg:left-64 lg:px-8 lg:py-4">
        <div className="min-w-0 shrink-0">
          <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-soft">Temps restant</p>
          <p className={`font-display text-base font-extrabold sm:text-lg ${expired ? 'text-muted' : 'text-red-600'}`}>
            {d == null ? '—' : expired ? 'Clôturé' : `${d} jour${d > 1 ? 's' : ''}`}
          </p>
        </div>
        <div className="flex items-center gap-2 sm:gap-3">
          <button
            onClick={() => navigator.clipboard?.writeText(window.location.href)}
            className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-line text-muted hover:bg-gray-50 sm:h-11 sm:w-11"
            title="Partager le lien"
          >
            <IconShare className="h-5 w-5" />
          </button>
          <button
            onClick={() => setStarred((v) => !v)}
            className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border sm:h-11 sm:w-11 ${
              starred ? 'border-gold bg-gold/10 text-gold' : 'border-line text-muted hover:bg-gray-50'
            }`}
            title="Suivre"
          >
            <IconStar className="h-5 w-5" fill={starred ? 'currentColor' : 'none'} />
          </button>
          <button
            onClick={() => window.print()}
            title="Exporter PDF"
            className="flex h-10 items-center gap-2 rounded-xl border border-line px-3 text-sm font-semibold text-ink hover:bg-gray-50 sm:h-11 sm:px-4"
          >
            <IconDownload className="h-4 w-4" />
            <span className="hidden sm:inline">Exporter PDF</span>
          </button>
          <button
            onClick={() => navigate('/notifications')}
            title="Créer une alerte similaire"
            className="flex h-10 items-center gap-2 rounded-xl bg-orange px-3 text-sm font-semibold text-white hover:bg-orange-dark sm:h-11 sm:px-5"
          >
            <IconBell className="h-4 w-4" />
            <span className="hidden sm:inline">Créer une alerte similaire</span>
          </button>
        </div>
      </div>
    </div>
  )
}
