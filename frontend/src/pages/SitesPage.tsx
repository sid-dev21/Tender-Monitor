import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { createSite, deleteSite, listSites, scrapeSite, testSite, updateSite } from '../api/sites'
import type { Site, SiteTestResult } from '../api/sites'
import { listTenders } from '../api/tenders'
import { IconLink, IconSources, IconShield, IconGlobe, IconPencil, IconTrash } from '../components/icons'
import { relativeTime, hostOf } from '../lib/format'
import { initials } from '../lib/user'

const CARD_ACCENT = ['border-t-blue-500', 'border-t-emerald-500', 'border-t-amber-500', 'border-t-violet-500']
const CARD_ICON = [
  { cls: 'bg-blue-50 text-blue-500', Icon: IconSources },
  { cls: 'bg-emerald-50 text-emerald-600', Icon: IconShield },
  { cls: 'bg-amber-50 text-amber-500', Icon: IconGlobe },
  { cls: 'bg-violet-50 text-violet-500', Icon: IconLink },
]

function AddSourceModal({ onClose }: { onClose: () => void }) {
  const qc = useQueryClient()
  const [name, setName] = useState('')
  const [url, setUrl] = useState('')
  const [contentType, setContentType] = useState<'' | 'html' | 'pdf'>('')

  const mutation = useMutation({
    mutationFn: () => createSite({ name, base_url: url, content_type: contentType || null }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['sites'] })
      onClose()
    },
  })

  const inputCls =
    'rounded-lg border border-line px-4 py-2.5 text-base outline-none focus:border-orange focus:ring-2 focus:ring-orange/15'

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" onClick={onClose}>
      <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl" onClick={(e) => e.stopPropagation()}>
        <h3 className="font-display text-lg font-bold text-ink">Ajouter une source</h3>
        <p className="mt-1 text-sm text-muted">
          Renseignez l'URL — le type de contenu est détecté automatiquement. Aucune ligne de code.
        </p>
        <form
          className="mt-5 flex flex-col gap-4"
          onSubmit={(e) => {
            e.preventDefault()
            mutation.mutate()
          }}
        >
          <label className="flex flex-col gap-1.5 text-sm font-semibold text-ink">
            Nom
            <input required value={name} onChange={(e) => setName(e.target.value)} placeholder="ex. SONABEL — Appels en cours" className={inputCls} />
          </label>
          <label className="flex flex-col gap-1.5 text-sm font-semibold text-ink">
            URL
            <input required type="url" value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://exemple.bf/appels-offres" className={inputCls} />
          </label>
          <label className="flex flex-col gap-1.5 text-sm font-semibold text-ink">
            Type de contenu
            <select value={contentType} onChange={(e) => setContentType(e.target.value as '' | 'html' | 'pdf')} className={inputCls}>
              <option value="">Détection automatique</option>
              <option value="html">HTML (données dans la page)</option>
              <option value="pdf">PDF (documents à télécharger)</option>
            </select>
          </label>
          {mutation.isError && (
            <p className="rounded-lg bg-red-50 px-4 py-2 text-sm text-red-700">Impossible d'ajouter la source. Vérifiez l'URL.</p>
          )}
          <div className="mt-2 flex justify-end gap-3">
            <button type="button" onClick={onClose} className="rounded-lg px-4 py-2.5 text-sm text-muted hover:bg-gray-100">
              Annuler
            </button>
            <button type="submit" disabled={mutation.isPending} className="rounded-lg bg-orange px-5 py-2.5 text-sm font-semibold text-white hover:bg-orange-dark disabled:opacity-60">
              {mutation.isPending ? 'Ajout…' : 'Ajouter'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

function TestResultPanel({ result, onUseSuggestion }: { result: SiteTestResult; onUseSuggestion: (url: string, label: string) => void }) {
  if (result.count === 0) {
    return (
      <div className="mt-3 rounded-lg border border-gold/40 bg-amber-50/50 p-4">
        <p className="text-sm font-semibold text-ink">Aucun appel d'offres trouvé sur cette page.</p>
        {result.suggested_links.length > 0 ? (
          <>
            <p className="mt-1 text-xs text-muted">Pages probables détectées — cliquez pour en ajouter une :</p>
            <div className="mt-2 flex flex-wrap gap-2">
              {result.suggested_links.map((link) => (
                <button
                  key={link.url}
                  onClick={() => onUseSuggestion(link.url, link.label)}
                  title={link.url}
                  className="rounded-full border border-navy/20 bg-white px-3 py-1.5 text-xs font-medium text-navy hover:border-orange hover:text-orange"
                >
                  {link.label} →
                </button>
              ))}
            </div>
          </>
        ) : (
          <p className="mt-1 text-xs text-muted">Astuce : renseignez l'URL exacte de la page qui liste les appels d'offres.</p>
        )}
      </div>
    )
  }
  return (
    <div className="mt-3 rounded-lg border border-gold/40 bg-amber-50/50 p-4">
      <p className="text-sm font-semibold text-ink">
        {result.count} appel(s) d'offres trouvé(s) <span className="font-normal text-muted">(aperçu — non enregistré)</span>
      </p>
      <ul className="mt-2 flex flex-col gap-2">
        {result.tenders.slice(0, 5).map((t, i) => (
          <li key={i} className="rounded-md bg-white px-3 py-2 text-sm shadow-sm">
            <div className="font-medium text-ink">{t.title ?? t.reference_number ?? '—'}</div>
            <div className="mt-0.5 flex gap-4 text-xs text-muted">
              {t.reference_number && <span>Réf. {t.reference_number}</span>}
              {t.deadline && <span>Échéance {new Date(t.deadline).toLocaleDateString('fr-FR')}</span>}
              {t.estimated_budget != null && <span>{t.estimated_budget.toLocaleString('fr-FR')} {t.currency}</span>}
            </div>
          </li>
        ))}
      </ul>
    </div>
  )
}

function SourceRow({ site }: { site: Site }) {
  const qc = useQueryClient()
  const [result, setResult] = useState<SiteTestResult | null>(null)

  const toggle = useMutation({
    mutationFn: () => updateSite(site.id, { is_active: !site.is_active }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['sites'] }),
  })
  const remove = useMutation({
    mutationFn: () => deleteSite(site.id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['sites'] }),
  })
  const test = useMutation({ mutationFn: () => testSite(site.id), onSuccess: setResult })
  const addSuggested = useMutation({
    mutationFn: (v: { url: string; label: string }) => createSite({ name: v.label || site.name, base_url: v.url }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['sites'] }),
  })
  const scrape = useMutation({
    mutationFn: () => scrapeSite(site.id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['tenders'] })
      qc.invalidateQueries({ queryKey: ['sites'] })
    },
  })

  return (
    <div className="rounded-xl border border-line bg-white p-4 shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex min-w-0 items-center gap-4">
          <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-navy text-sm font-bold text-gold">
            {initials(site.name)}
          </div>
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <span className="truncate text-sm font-bold text-ink">{site.name}</span>
              <span className="rounded bg-gray-100 px-1.5 py-0.5 text-[10px] font-bold uppercase text-muted">{site.content_type}</span>
            </div>
            <a href={site.base_url} target="_blank" rel="noreferrer" className="block truncate text-xs text-blue-600 hover:underline">
              {site.base_url}
            </a>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button onClick={() => test.mutate()} disabled={test.isPending} className="rounded-lg border border-line px-3 py-1.5 text-xs font-semibold text-muted hover:bg-gray-50 disabled:opacity-60">
            {test.isPending ? 'Test…' : 'Tester'}
          </button>
          <button onClick={() => scrape.mutate()} disabled={scrape.isPending} className="rounded-lg bg-orange px-3 py-1.5 text-xs font-semibold text-white hover:bg-orange-dark disabled:opacity-60">
            {scrape.isPending ? 'Scan…' : 'Scanner'}
          </button>
          <button
            onClick={() => toggle.mutate()}
            title={site.is_active ? 'Désactiver' : 'Activer'}
            className={`relative h-6 w-11 shrink-0 rounded-full transition-colors ${site.is_active ? 'bg-orange' : 'bg-line'}`}
          >
            <span className={`absolute top-0.5 flex h-5 w-5 items-center justify-center rounded-full bg-white transition-all ${site.is_active ? 'left-[22px]' : 'left-0.5'}`} />
          </button>
          <button className="p-1.5 text-muted-soft hover:text-navy" title="Modifier (tester)" onClick={() => test.mutate()}>
            <IconPencil className="h-4 w-4" />
          </button>
          <button
            onClick={() => { if (confirm(`Supprimer « ${site.name} » ?`)) remove.mutate() }}
            className="p-1.5 text-muted-soft hover:text-red-600"
            title="Supprimer"
          >
            <IconTrash className="h-4 w-4" />
          </button>
        </div>
      </div>

      {test.isError && <p className="mt-3 rounded-lg bg-red-50 px-4 py-2 text-sm text-red-700">Le test a échoué (site injoignable ou bloqué).</p>}
      {scrape.data && (
        <p className="mt-3 rounded-lg bg-emerald-50 px-4 py-2 text-sm text-emerald-700">
          Scan terminé : {scrape.data.tenders_found} appel(s) d'offres enregistré(s).
          {scrape.data.errors.length > 0 && ` (${scrape.data.errors.length} erreur(s))`}
        </p>
      )}
      {scrape.isError && <p className="mt-3 rounded-lg bg-red-50 px-4 py-2 text-sm text-red-700">Le scan a échoué (site injoignable ou bloqué).</p>}
      {result && <TestResultPanel result={result} onUseSuggestion={(url, label) => addSuggested.mutate({ url, label })} />}
    </div>
  )
}

export function SitesPage() {
  const [showAdd, setShowAdd] = useState(false)
  const { data: sites, isLoading } = useQuery({ queryKey: ['sites'], queryFn: listSites })
  const { data: tenders } = useQuery({ queryKey: ['tenders', ''], queryFn: () => listTenders() })

  const counts = useMemo(() => {
    const m = new Map<string, number>()
    for (const t of tenders ?? []) m.set(t.source_site_id, (m.get(t.source_site_id) ?? 0) + 1)
    return m
  }, [tenders])

  const active = (sites ?? []).filter((s) => s.is_active).slice(0, 3)

  return (
    <div>
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="font-display text-3xl font-extrabold text-ink">Sources de données</h1>
          <p className="mt-1 text-sm text-muted">Gérez les portails et flux institutionnels indexés par Tender Monitor.</p>
        </div>
        <button
          onClick={() => setShowAdd(true)}
          className="flex items-center gap-2 rounded-xl bg-orange px-5 py-3 text-sm font-semibold text-white shadow-sm hover:bg-orange-dark"
        >
          <IconLink className="h-4 w-4" />
          Ajouter une source
        </button>
      </div>

      {/* active showcase cards */}
      {active.length > 0 && (
        <>
          <h2 className="mt-8 flex items-center gap-2 text-sm font-extrabold uppercase tracking-wide text-ink">
            <IconShield className="h-4 w-4 text-muted-soft" />
            Sources surveillées
          </h2>
          <div className="mt-4 grid grid-cols-1 gap-5 md:grid-cols-2 xl:grid-cols-3">
            {active.map((s, i) => {
              const { cls, Icon } = CARD_ICON[i % CARD_ICON.length]
              return (
                <div key={s.id} className={`rounded-2xl border border-line border-t-4 ${CARD_ACCENT[i % CARD_ACCENT.length]} bg-white p-6 shadow-sm`}>
                  <div className="flex items-start justify-between">
                    <span className={`flex h-12 w-12 items-center justify-center rounded-xl ${cls}`}>
                      <Icon className="h-6 w-6" />
                    </span>
                    <span className="flex items-center gap-1.5 text-xs font-bold uppercase text-emerald-600">
                      <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                      Actif
                    </span>
                  </div>
                  <h3 className="mt-4 font-display text-xl font-extrabold text-ink">{s.name}</h3>
                  <p className="mt-1 truncate text-sm text-muted">{hostOf(s.base_url)}</p>
                  <div className="mt-6 flex items-end justify-between border-t border-line pt-4">
                    <div>
                      <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-soft">Marchés</p>
                      <p className="mt-0.5 font-display text-xl font-extrabold text-ink">{(counts.get(s.id) ?? 0).toLocaleString('fr-FR')}</p>
                    </div>
                    <div className="text-right">
                      <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-soft">Ajoutée</p>
                      <p className="mt-0.5 text-xs text-muted">{relativeTime(s.created_at)}</p>
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        </>
      )}

      {/* all sources — managed list */}
      <h2 className="mt-10 flex items-center gap-2 text-sm font-extrabold uppercase tracking-wide text-ink">
        <IconSources className="h-4 w-4 text-muted-soft" />
        Toutes mes sources
      </h2>
      <div className="mt-4 flex flex-col gap-4">
        {isLoading && <p className="text-muted">Chargement…</p>}
        {!isLoading && sites?.length === 0 && (
          <div className="rounded-2xl border border-dashed border-line bg-white p-10 text-center text-muted">
            Aucune source pour l'instant. Cliquez sur « Ajouter une source » pour commencer.
          </div>
        )}
        {sites?.map((site) => (
          <SourceRow key={site.id} site={site} />
        ))}
      </div>

      {showAdd && <AddSourceModal onClose={() => setShowAdd(false)} />}
    </div>
  )
}
