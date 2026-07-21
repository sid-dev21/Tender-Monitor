import { api } from './client'

export interface Tender {
  id: string
  title: string
  reference_number: string
  publication_date: string | null
  deadline: string | null
  contracting_authority: string | null
  estimated_budget: number | null
  currency: string
  status: string
  document_url: string | null
  source_site_id: string
  matched_keywords: string[]
  created_at: string
  // Populated only after a call to scoreMyTenders() — null everywhere else.
  // The label is what the model actually decided and what we display; the
  // score is derived from it purely to order the list, and is never shown as
  // a percentage (it would imply a precision the model does not have).
  relevance_label: RelevanceLabel | null
  relevance_score: number | null
  relevance_reason: string | null
}

export type RelevanceLabel = 'correspond' | 'connexe' | 'hors_metier' | 'indisponible'

export async function listTenders(keywords?: string): Promise<Tender[]> {
  const { data } = await api.get<Tender[]>('/api/tenders', {
    params: keywords ? { keywords } : undefined,
  })
  return data
}

/**
 * On-demand semantic scoring (local LLM via Ollama) of the current user's
 * keyword-matched tenders against their company profile. Capped server-side
 * (settings.score_max_tenders) — can take a few seconds per tender, so callers
 * should show a loading state rather than treat this like a normal GET.
 */
export async function scoreMyTenders(keywords?: string): Promise<Tender[]> {
  const { data } = await api.post<Tender[]>(
    '/api/tenders/score',
    {},
    { params: keywords ? { keywords } : undefined },
  )
  return data
}
