import { Link } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { listTenders } from '../api/tenders'
import type { Tender } from '../api/tenders'
import { listSites } from '../api/sites'
import {
  IconTenders,
  IconCheck,
  IconWarning,
  IconLink,
  IconDownload,
  IconRefresh,
} from '../components/icons'
import { deadlineLabel, relativeTime, todayLong, hostOf } from '../lib/format'

type Accent = 'gold' | 'navy' | 'red' | 'green'

const ACCENT_BAR: Record<Accent, string> = {
  gold: 'bg-gold',
  navy: 'bg-navy',
  red: 'bg-red-500',
  green: 'bg-emerald-500',
}
const ACCENT_ICON: Record<Accent, string> = {
  gold: 'bg-gold/10 text-gold',
  navy: 'bg-navy/10 text-navy',
  red: 'bg-red-50 text-red-500',
  green: 'bg-emerald-50 text-emerald-600',
}
const ACCENT_CHIP: Record<Accent, string> = {
  gold: 'bg-gold/10 text-gold',
  navy: 'bg-navy/[0.06] text-navy',
  red: 'bg-red-50 text-red-600',
  green: 'bg-emerald-50 text-emerald-600',
}

function StatCard({
  label,
  value,
  chip,
  Icon,
  accent,
  highlight,
}: {
  label: string
  value: number
  chip: string
  Icon: (p: { className?: string }) => React.ReactElement
  accent: Accent
  highlight?: boolean
}) {
  return (
    <div
      className={`relative overflow-hidden rounded-2xl border bg-white p-5 shadow-sm transition-shadow hover:shadow-md ${
        highlight ? 'border-red-200 ring-1 ring-red-100' : 'border-line'
      }`}
    >
      <div className="flex items-start justify-between">
        <span className={`flex h-11 w-11 items-center justify-center rounded-xl ${ACCENT_ICON[accent]}`}>
          <Icon className="h-5 w-5" />
        </span>
        <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${ACCENT_CHIP[accent]}`}>{chip}</span>
      </div>
      <p className="mt-4 text-sm text-muted">{label}</p>
      <p className="mt-0.5 font-display text-4xl font-extrabold text-ink">{value.toLocaleString('fr-FR')}</p>
      <span className={`absolute bottom-0 left-0 h-1 w-24 ${ACCENT_BAR[accent]}`} />
    </div>
  )
}

const TONE_PILL: Record<string, string> = {
  urgent: 'bg-red-50 text-red-600',
  soon: 'bg-amber-50 text-amber-700',
  ok: 'bg-emerald-50 text-emerald-700',
  expired: 'bg-gray-100 text-muted',
  none: 'bg-gray-100 text-muted',
}

function csvExport(tenders: Tender[]) {
  const head = ['Titre', 'Référence', 'Autorité', 'Date limite', 'Budget', 'Devise', 'Statut', 'Source']
  const rows = tenders.map((t) => [
    t.title,
    t.reference_number,
    t.contracting_authority ?? '',
    t.deadline ?? '',
    t.estimated_budget ?? '',
    t.currency,
    t.status,
    hostOf(t.document_url),
  ])
  const body = [head, ...rows]
    .map((r) => r.map((c) => `"${String(c).replace(/"/g, '""')}"`).join(','))
    .join('\n')
  const url = URL.createObjectURL(new Blob(['﻿' + body], { type: 'text/csv;charset=utf-8' }))
  const a = document.createElement('a')
  a.href = url
  a.download = 'appels-offres.csv'
  a.click()
  URL.revokeObjectURL(url)
}

/** Tender counts per calendar month over the last 6 months. */
function monthlyHistogram(tenders: Tender[]): { label: string; count: number }[] {
  const buckets: { key: string; label: string; count: number }[] = []
  const now = new Date()
  for (let i = 5; i >= 0; i--) {
    const d = new Date(now.getFullYear(), now.getMonth() - i, 1)
    buckets.push({
      key: `${d.getFullYear()}-${d.getMonth()}`,
      label: d.toLocaleDateString('fr-FR', { month: 'short' }),
      count: 0,
    })
  }
  const idx = new Map(buckets.map((b, i) => [b.key, i]))
  for (const t of tenders) {
    const d = new Date(t.created_at)
    const i = idx.get(`${d.getFullYear()}-${d.getMonth()}`)
    if (i != null) buckets[i].count++
  }
  return buckets
}

const ALERT_BAR = ['border-l-orange', 'border-l-gold', 'border-l-navy', 'border-l-emerald-500']
const ALERT_KW = ['text-orange', 'text-gold', 'text-navy', 'text-emerald-600']

export function DashboardPage() {
  const qc = useQueryClient()
  const { data: tenders } = useQuery({ queryKey: ['tenders', ''], queryFn: () => listTenders() })
  const { data: sites } = useQuery({ queryKey: ['sites'], queryFn: listSites })

  const all = tenders ?? []
  const siteName = new Map((sites ?? []).map((s) => [s.id, s.name]))

  const weekAgo = Date.now() - 7 * 86_400_000
  const newCount = all.filter((t) => new Date(t.created_at).getTime() >= weekAgo).length
  const activeCount = all.filter((t) => {
    const dl = t.deadline ? new Date(t.deadline).getTime() : null
    return dl == null || dl >= Date.now()
  }).length
  const reviewCount = all.filter((t) => t.status !== 'parsed').length
  const activeSources = (sites ?? []).filter((s) => s.is_active).length

  const recent = all.slice(0, 4)
  const alerts = (all.filter((t) => t.matched_keywords.length > 0).length
    ? all.filter((t) => t.matched_keywords.length > 0)
    : all
  ).slice(0, 4)
  const histogram = monthlyHistogram(all)
  const maxBar = Math.max(1, ...histogram.map((b) => b.count))

  const topSources = Object.entries(
    all.reduce<Record<string, number>>((acc, t) => {
      const name = siteName.get(t.source_site_id) ?? hostOf(t.document_url) ?? 'Source'
      acc[name] = (acc[name] ?? 0) + 1
      return acc
    }, {}),
  )
    .sort((a, b) => b[1] - a[1])
    .slice(0, 2)
    .map(([name]) => name)

  return (
    <div>
      {/* header */}
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="font-display text-2xl font-extrabold text-ink sm:text-3xl">Tableau de bord</h1>
          <p className="mt-1 text-sm text-muted">
            {todayLong()} — <span className="italic">données actualisées à l'instant</span>
          </p>
        </div>
        <div className="flex flex-wrap gap-3">
          <button
            onClick={() => csvExport(all)}
            className="flex items-center gap-2 rounded-xl border border-line bg-white px-4 py-2.5 text-sm font-semibold text-ink shadow-sm transition-colors hover:bg-gray-50"
          >
            <IconDownload className="h-4 w-4" />
            Exporter Rapport
          </button>
          <button
            onClick={() => {
              qc.invalidateQueries({ queryKey: ['tenders'] })
              qc.invalidateQueries({ queryKey: ['sites'] })
            }}
            className="flex items-center gap-2 rounded-xl bg-orange px-4 py-2.5 text-sm font-semibold text-white shadow-sm shadow-orange/20 transition-colors hover:bg-orange-dark"
          >
            <IconRefresh className="h-4 w-4" />
            Actualiser
          </button>
        </div>
      </div>

      {/* stat cards */}
      <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Nouveaux" value={newCount} chip="7 derniers jours" Icon={IconTenders} accent="gold" />
        <StatCard label="Actifs" value={activeCount} chip="en cours" Icon={IconCheck} accent="navy" />
        <StatCard label="À vérifier" value={reviewCount} chip="à traiter" Icon={IconWarning} accent="red" highlight />
        <StatCard label="Sources actives" value={activeSources} chip="surveillées" Icon={IconLink} accent="green" />
      </div>

      {/* two columns */}
      <div className="mt-6 grid grid-cols-1 gap-6 xl:grid-cols-3">
        {/* recent tenders */}
        <div className="rounded-2xl border border-line bg-white p-5 shadow-sm sm:p-6 xl:col-span-2">
          <div className="flex items-center justify-between">
            <h2 className="font-display text-lg font-bold text-ink">Appels d'offres récents</h2>
            <Link to="/tenders" className="text-sm font-semibold text-orange hover:underline">
              Voir tout
            </Link>
          </div>

          {recent.length === 0 ? (
            <div className="mt-6 rounded-xl border border-dashed border-line p-8 text-center text-sm text-muted">
              Rien pour l'instant.{' '}
              <Link to="/sites" className="font-semibold text-orange hover:underline">
                Ajoutez une source
              </Link>{' '}
              pour lancer votre veille.
            </div>
          ) : (
            <div className="mt-4 -mx-1 overflow-x-auto">
              <table className="w-full min-w-[34rem]">
                <thead>
                  <tr className="border-b border-line text-left text-xs font-semibold uppercase tracking-wide text-muted-soft">
                    <th className="pb-3 pr-4 font-semibold">Source</th>
                    <th className="pb-3 pr-4 font-semibold">Titre</th>
                    <th className="pb-3 pr-4 font-semibold">Catégorie</th>
                    <th className="pb-3 font-semibold">Échéance</th>
                  </tr>
                </thead>
                <tbody>
                  {recent.map((t) => {
                    const dl = deadlineLabel(t.deadline)
                    const source = siteName.get(t.source_site_id) ?? hostOf(t.document_url) ?? 'Source'
                    const category = t.matched_keywords[0]?.toUpperCase() ?? 'BTP'
                    return (
                      <tr
                        key={t.id}
                        className="border-b border-line/70 transition-colors last:border-0 hover:bg-gray-50/60"
                      >
                        <td className="py-4 pr-4 align-top">
                          <span className="inline-block max-w-[9rem] truncate rounded bg-navy/5 px-2 py-1 text-xs font-semibold uppercase text-navy">
                            {source}
                          </span>
                        </td>
                        <td className="py-4 pr-4 align-top">
                          <Link to={`/tenders/${t.id}`} className="text-sm font-semibold text-ink hover:text-orange">
                            {t.title}
                          </Link>
                          {t.contracting_authority && (
                            <p className="mt-0.5 text-xs text-muted-soft">{t.contracting_authority}</p>
                          )}
                        </td>
                        <td className="py-4 pr-4 align-top text-sm text-muted">{category}</td>
                        <td className="py-4 align-top">
                          <span
                            className={`whitespace-nowrap rounded-lg px-2.5 py-1 text-xs font-semibold ${TONE_PILL[dl.tone]}`}
                          >
                            {dl.text}
                          </span>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* latest alerts */}
        <div className="flex flex-col rounded-2xl border border-line bg-white p-5 shadow-sm sm:p-6">
          <h2 className="font-display text-lg font-bold text-ink">Dernières alertes</h2>
          <div className="mt-4 flex flex-1 flex-col gap-3">
            {alerts.length === 0 && <p className="text-sm text-muted">Aucune alerte récente.</p>}
            {alerts.map((t, i) => {
              const source = siteName.get(t.source_site_id) ?? hostOf(t.document_url) ?? 'Source'
              const kw = t.matched_keywords[0]?.toUpperCase()
              const score = t.relevance_score != null ? Math.round(t.relevance_score * 100) : null
              return (
                <div
                  key={t.id}
                  className={`rounded-lg border border-line border-l-4 ${ALERT_BAR[i % 4]} bg-gray-50/60 p-3`}
                >
                  <div className="flex items-center justify-between gap-2">
                    {kw ? (
                      <span className={`text-xs font-bold uppercase tracking-wide ${ALERT_KW[i % 4]}`}>
                        Mot-clé : {kw}
                      </span>
                    ) : (
                      <span className="text-xs font-bold uppercase tracking-wide text-muted-soft">Nouvel appel</span>
                    )}
                    <span className="shrink-0 text-xs text-muted-soft">{relativeTime(t.created_at)}</span>
                  </div>
                  <p className="mt-1 line-clamp-2 text-sm font-semibold text-ink">{t.title}</p>
                  <div className="mt-2 flex flex-wrap items-center gap-1.5">
                    <span className="max-w-full truncate rounded border border-line bg-white px-2 py-0.5 text-[11px] font-medium uppercase text-muted">
                      Source : {source}
                    </span>
                    {score != null && (
                      <span className="rounded border border-line bg-white px-2 py-0.5 text-[11px] font-medium uppercase text-muted">
                        Score : {score}%
                      </span>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
          <Link
            to="/notifications"
            className="mt-4 rounded-xl border border-navy py-2.5 text-center text-sm font-semibold text-navy transition-colors hover:bg-navy hover:text-white"
          >
            Gérer les alertes
          </Link>
        </div>
      </div>

      {/* performance card */}
      <div className="mt-6 grid grid-cols-1 gap-6 overflow-hidden rounded-2xl bg-navy p-6 text-white sm:p-8 lg:grid-cols-2">
        <div>
          <h2 className="font-display text-xl font-extrabold text-gold sm:text-2xl">
            Analyse de Performance Trimestrielle
          </h2>
          <p className="mt-3 max-w-md text-sm leading-relaxed text-white/70">
            {all.length > 0 ? (
              <>
                <span className="font-semibold text-white">{all.length}</span> appels d'offres suivis sur vos
                sources.{' '}
                {topSources.length > 0 && (
                  <>
                    Vos canaux les plus prolifiques :{' '}
                    <span className="font-semibold text-white">{topSources.join(' et ')}</span>.
                  </>
                )}
              </>
            ) : (
              <>Ajoutez des sources et lancez un scan pour voir vos statistiques de veille apparaître ici.</>
            )}
          </p>
          <div className="mt-6 flex gap-10">
            <div>
              <p className="font-display text-3xl font-extrabold">{all.length.toLocaleString('fr-FR')}</p>
              <p className="mt-1 text-xs text-white/60">Appels d'offres suivis</p>
            </div>
            <div className="border-l border-white/15 pl-10">
              <p className="font-display text-3xl font-extrabold">{activeSources}</p>
              <p className="mt-1 text-xs text-white/60">Sources analysées</p>
            </div>
          </div>
        </div>
        <div className="flex items-end justify-end gap-2 rounded-xl bg-white/[0.04] p-4 sm:gap-3 sm:p-6">
          {histogram.map((b) => (
            <div key={b.label} className="flex flex-1 flex-col items-center gap-2">
              <div className="flex h-40 w-full items-end justify-center">
                <div
                  className="w-6 rounded-t-md bg-gradient-to-t from-gold/40 to-gold sm:w-8"
                  style={{ height: `${Math.max(6, (b.count / maxBar) * 100)}%` }}
                  title={`${b.count} appels d'offres`}
                />
              </div>
              <span className="text-xs capitalize text-white/50">{b.label}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
