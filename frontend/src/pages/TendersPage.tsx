import { useMemo, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { listTenders, scoreMyTenders } from '../api/tenders'
import type { Tender, RelevanceLabel } from '../api/tenders'
import { listSites } from '../api/sites'
import { IconPin, IconChevronLeft, IconChevronRight, IconSearch, IconStar } from '../components/icons'
import { fmtDateShort, daysLeft, hostOf } from '../lib/format'
import { errorMessage } from '../lib/errors'

interface ScoreInfo {
  label: RelevanceLabel
  score: number
  reason: string
}

/** The model picks one of these; we show the verdict, not a made-up percentage. */
const RELEVANCE_BADGE: Record<RelevanceLabel, { text: string; cls: string }> = {
  correspond: { text: 'Correspond', cls: 'bg-emerald-50 text-emerald-700' },
  connexe: { text: 'Connexe', cls: 'bg-amber-50 text-amber-700' },
  hors_metier: { text: 'Hors métier', cls: 'bg-gray-100 text-muted' },
  indisponible: { text: 'IA indisponible', cls: 'bg-gray-100 text-muted-soft' },
}

const PAGE_SIZE = 9

type StatusKind = { label: string; cls: string; dot?: boolean }

function statusOf(t: Tender): StatusKind {
  const d = daysLeft(t.deadline)
  if (d != null && d < 0) return { label: 'Expiré', cls: 'bg-gray-100 text-muted' }
  if (d != null && d <= 3) return { label: 'Urgent', cls: 'bg-red-50 text-red-600', dot: true }
  const fresh = Date.now() - new Date(t.created_at).getTime() < 3 * 86_400_000
  if (fresh) return { label: 'Nouveau', cls: 'bg-violet-50 text-violet-600' }
  if (t.status !== 'parsed') return { label: 'À vérifier', cls: 'bg-amber-50 text-amber-700' }
  return { label: 'Ouvert', cls: 'bg-emerald-50 text-emerald-700' }
}

function TenderCard({
  tender,
  source,
  scoreInfo,
  onOpen,
}: {
  tender: Tender
  source: string
  scoreInfo?: ScoreInfo
  onOpen: () => void
}) {
  const st = statusOf(tender)
  const d = daysLeft(tender.deadline)
  const urgent = d != null && d >= 0 && d <= 3
  const tags = [...new Set(['BTP', ...tender.matched_keywords.map((k) => k.toUpperCase())])].slice(0, 3)

  return (
    <button
      onClick={onOpen}
      className="flex h-full flex-col rounded-2xl border border-line bg-white p-5 text-left shadow-sm transition-all hover:-translate-y-0.5 hover:border-orange/40 hover:shadow-md"
    >
      <div className="flex items-center justify-between gap-2">
        <span className="max-w-[8rem] truncate text-xs font-bold uppercase tracking-wide text-muted-soft">
          {source}
        </span>
        <div className="flex items-center gap-1.5">
          {scoreInfo && (
            <span
              title={scoreInfo.reason}
              className={`flex items-center gap-1 rounded-full px-2.5 py-1 text-[11px] font-bold ${RELEVANCE_BADGE[scoreInfo.label].cls}`}
            >
              <IconStar className="h-3 w-3" />
              {RELEVANCE_BADGE[scoreInfo.label].text}
            </span>
          )}
          <span className={`flex items-center gap-1 rounded-full px-2.5 py-1 text-[11px] font-bold uppercase ${st.cls}`}>
            {st.dot && <span className="h-1.5 w-1.5 rounded-full bg-current" />}
            {st.label}
          </span>
        </div>
      </div>

      <h3 className="mt-3 line-clamp-2 font-display text-base font-bold leading-snug text-ink">{tender.title}</h3>
      <p className="mt-1 text-xs italic text-muted-soft">Réf : {tender.reference_number}</p>
      {scoreInfo && <p className="mt-1 line-clamp-2 text-xs text-muted">{scoreInfo.reason}</p>}

      <div className="mt-3 flex flex-wrap gap-1.5">
        {tags.map((tag) => (
          <span key={tag} className="rounded bg-navy/5 px-2 py-0.5 text-[11px] font-semibold text-navy">
            {tag}
          </span>
        ))}
      </div>

      {tender.contracting_authority && (
        <p className="mt-3 flex items-center gap-1.5 text-xs text-muted">
          <IconPin className="h-4 w-4 shrink-0 text-muted-soft" />
          <span className="truncate">{tender.contracting_authority}</span>
        </p>
      )}

      <div className="mt-auto flex items-end justify-between gap-3 border-t border-line pt-4">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-soft">Budget estimé</p>
          <p className="mt-0.5 font-display text-lg font-extrabold text-ink">
            {tender.estimated_budget != null ? (
              <>
                {tender.estimated_budget.toLocaleString('fr-FR')}{' '}
                <span className="text-xs font-bold">{tender.currency}</span>
              </>
            ) : (
              <span className="text-sm text-muted">—</span>
            )}
          </p>
        </div>
        {tender.deadline && (
          <div className={`rounded-lg px-3 py-2 text-center ${urgent ? 'bg-orange/10' : 'bg-gray-50'}`}>
            <p className="text-[10px] font-semibold uppercase text-muted-soft">Deadline</p>
            <p className={`text-xs font-bold ${urgent ? 'text-orange' : 'text-ink'}`}>
              {fmtDateShort(tender.deadline)}
            </p>
          </div>
        )}
      </div>
    </button>
  )
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="flex flex-col gap-1.5">
      <span className="text-xs font-semibold uppercase tracking-wide text-muted-soft">{label}</span>
      {children}
    </label>
  )
}

const selectCls =
  'rounded-lg border border-line bg-white px-3 py-2.5 text-sm text-ink outline-none focus:border-orange focus:ring-2 focus:ring-orange/15'

export function TendersPage() {
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const initialQ = params.get('q') ?? ''

  // Applied filters drive the query; draft filters hold pending UI state.
  const [applied, setApplied] = useState({ q: initialQ, source: '', status: '', from: '' })
  const [draft, setDraft] = useState({ q: initialQ, source: '', status: '', from: '' })
  const [view, setView] = useState<'grid' | 'list'>('grid')
  const [page, setPage] = useState(1)
  const [scores, setScores] = useState<Map<string, ScoreInfo>>(new Map())
  const [scoring, setScoring] = useState(false)
  const [scoreError, setScoreError] = useState<string | null>(null)

  const { data: sites } = useQuery({ queryKey: ['sites'], queryFn: listSites })
  const { data: tenders, isLoading } = useQuery({
    queryKey: ['tenders', applied.q],
    queryFn: () => listTenders(applied.q || undefined),
  })

  const siteName = useMemo(() => new Map((sites ?? []).map((s) => [s.id, s.name])), [sites])

  const filtered = useMemo(() => {
    const base = (tenders ?? []).filter((t) => {
      if (applied.source && t.source_site_id !== applied.source) return false
      if (applied.status) {
        const d = daysLeft(t.deadline)
        if (applied.status === 'open' && d != null && d < 0) return false
        if (applied.status === 'expired' && !(d != null && d < 0)) return false
      }
      if (applied.from && t.publication_date && new Date(t.publication_date) < new Date(applied.from)) return false
      return true
    })
    if (scores.size === 0) return base
    // Scored tenders first, ranked by relevance; unscored ones keep their place after.
    return [...base].sort((a, b) => (scores.get(b.id)?.score ?? -1) - (scores.get(a.id)?.score ?? -1))
  }, [tenders, applied, scores])

  async function runScoring() {
    setScoring(true)
    setScoreError(null)
    try {
      const result = await scoreMyTenders(applied.q || undefined)
      setScores(
        new Map(
          result
            .filter((t) => t.relevance_label != null)
            .map((t) => [
              t.id,
              {
                label: t.relevance_label as RelevanceLabel,
                score: t.relevance_score ?? 0,
                reason: t.relevance_reason ?? '',
              },
            ]),
        ),
      )
      setPage(1)

      // A reachable API that returns nothing but "indisponible" means the model
      // itself is absent — the public demo runs without it. Say so plainly,
      // rather than leaving a row of grey badges that read like a bug.
      if (result.length > 0 && result.every((t) => t.relevance_label === 'indisponible')) {
        setScoreError(
          "L'analyse sémantique nécessite un modèle de langage local (Ollama), " +
            "absent de cette démonstration publique. Le reste de l'application " +
            'fonctionne normalement.',
        )
      }
    } catch (err) {
      setScoreError(errorMessage(err, "Échec de l'analyse IA. Le modèle local (Ollama) est-il joignable ?"))
    } finally {
      setScoring(false)
    }
  }

  const pageCount = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE))
  const current = Math.min(page, pageCount)
  const shown = filtered.slice((current - 1) * PAGE_SIZE, current * PAGE_SIZE)

  function apply() {
    setApplied(draft)
    setPage(1)
  }

  function open(t: Tender) {
    navigate(`/tenders/${t.id}`, { state: { tender: t } })
  }

  return (
    <div>
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="font-display text-3xl font-extrabold text-ink">Liste des Appels d'offres</h1>
          <p className="mt-1 text-sm text-muted">
            {filtered.length.toLocaleString('fr-FR')} résultats trouvés dans vos sources surveillées.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={runScoring}
            disabled={scoring}
            title="Note chaque appel d'offres par rapport à votre profil d'entreprise (IA locale)"
            className="flex items-center gap-1.5 rounded-lg bg-navy px-4 py-2 text-sm font-semibold text-white hover:bg-navy/90 disabled:opacity-60"
          >
            <IconStar className="h-4 w-4" />
            {scoring ? 'Analyse en cours… (~1 min)' : 'Analyser avec l’IA'}
          </button>
          <div className="flex overflow-hidden rounded-lg border border-line bg-white">
          {(['grid', 'list'] as const).map((v) => (
            <button
              key={v}
              onClick={() => setView(v)}
              className={`px-3 py-2 ${view === v ? 'bg-navy text-white' : 'text-muted hover:bg-gray-50'}`}
              aria-label={v === 'grid' ? 'Vue grille' : 'Vue liste'}
            >
              {v === 'grid' ? (
                <svg viewBox="0 0 24 24" className="h-4 w-4" fill="currentColor">
                  <rect x="3" y="3" width="8" height="8" rx="1" />
                  <rect x="13" y="3" width="8" height="8" rx="1" />
                  <rect x="3" y="13" width="8" height="8" rx="1" />
                  <rect x="13" y="13" width="8" height="8" rx="1" />
                </svg>
              ) : (
                <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M4 6h16M4 12h16M4 18h16" strokeLinecap="round" />
                </svg>
              )}
            </button>
          ))}
          </div>
        </div>
      </div>

      {scoreError && (
        <p className="mt-3 rounded-lg bg-amber-50 px-4 py-3 text-sm text-amber-800">{scoreError}</p>
      )}

      {/* filter bar */}
      <div className="mt-6 rounded-2xl border border-line bg-white p-5 shadow-sm">
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-[1fr_1fr_1fr_1fr_auto] lg:items-end">
          <Field label="Source">
            <select
              value={draft.source}
              onChange={(e) => setDraft({ ...draft, source: e.target.value })}
              className={selectCls}
            >
              <option value="">Toutes les sources</option>
              {(sites ?? []).map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Catégorie / mot-clé">
            <div className="relative">
              <IconSearch className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-soft" />
              <input
                value={draft.q}
                onChange={(e) => setDraft({ ...draft, q: e.target.value })}
                onKeyDown={(e) => e.key === 'Enter' && apply()}
                placeholder="route, école…"
                className={`${selectCls} w-full pl-9`}
              />
            </div>
          </Field>
          <Field label="Statut">
            <select
              value={draft.status}
              onChange={(e) => setDraft({ ...draft, status: e.target.value })}
              className={selectCls}
            >
              <option value="">Tous</option>
              <option value="open">Ouvert</option>
              <option value="expired">Expiré</option>
            </select>
          </Field>
          <Field label="Publié après">
            <input
              type="date"
              value={draft.from}
              onChange={(e) => setDraft({ ...draft, from: e.target.value })}
              className={selectCls}
            />
          </Field>
          <button
            onClick={apply}
            className="h-[42px] rounded-lg bg-navy px-6 text-sm font-semibold text-white hover:bg-navy/90"
          >
            Filtrer
          </button>
        </div>
      </div>

      {/* results */}
      {isLoading ? (
        <p className="mt-8 text-muted">Chargement…</p>
      ) : shown.length === 0 ? (
        <div className="mt-8 rounded-2xl border border-dashed border-line bg-white p-12 text-center text-muted">
          {applied.q || applied.source || applied.status || applied.from
            ? 'Aucun appel d\'offres ne correspond à ces filtres.'
            : "Aucun appel d'offres pour l'instant. Ajoutez une source et lancez un scan."}
        </div>
      ) : (
        <div
          className={
            view === 'grid'
              ? 'mt-6 grid grid-cols-1 gap-5 md:grid-cols-2 xl:grid-cols-3'
              : 'mt-6 flex flex-col gap-4'
          }
        >
          {shown.map((t) => (
            <TenderCard
              key={t.id}
              tender={t}
              source={siteName.get(t.source_site_id) ?? hostOf(t.document_url) ?? 'Source'}
              scoreInfo={scores.get(t.id)}
              onOpen={() => open(t)}
            />
          ))}
        </div>
      )}

      {/* pagination */}
      {filtered.length > PAGE_SIZE && (
        <div className="mt-8 flex items-center justify-between">
          <p className="text-sm text-muted">
            Affichage de {(current - 1) * PAGE_SIZE + 1}–{Math.min(current * PAGE_SIZE, filtered.length)} sur{' '}
            {filtered.length.toLocaleString('fr-FR')} résultats
          </p>
          <div className="flex items-center gap-1.5">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={current === 1}
              className="flex h-9 w-9 items-center justify-center rounded-lg border border-line bg-white text-muted disabled:opacity-40 hover:bg-gray-50"
            >
              <IconChevronLeft className="h-4 w-4" />
            </button>
            {Array.from({ length: pageCount }, (_, i) => i + 1)
              .filter((n) => n === 1 || n === pageCount || Math.abs(n - current) <= 1)
              .map((n, idx, arr) => (
                <span key={n} className="flex items-center">
                  {idx > 0 && arr[idx - 1] !== n - 1 && <span className="px-1 text-muted-soft">…</span>}
                  <button
                    onClick={() => setPage(n)}
                    className={`h-9 w-9 rounded-lg text-sm font-semibold ${
                      n === current ? 'bg-navy text-white' : 'border border-line bg-white text-muted hover:bg-gray-50'
                    }`}
                  >
                    {n}
                  </button>
                </span>
              ))}
            <button
              onClick={() => setPage((p) => Math.min(pageCount, p + 1))}
              disabled={current === pageCount}
              className="flex h-9 w-9 items-center justify-center rounded-lg border border-line bg-white text-muted disabled:opacity-40 hover:bg-gray-50"
            >
              <IconChevronRight className="h-4 w-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
