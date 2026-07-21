import { api } from './client'

export type ContentType = 'html' | 'pdf'

export interface Site {
  id: string
  name: string
  base_url: string
  content_type: ContentType
  is_active: boolean
  locale: string | null
  timezone: string | null
  created_at: string
}

export interface SiteCreate {
  name: string
  base_url: string
  content_type?: ContentType | null
  locale?: string | null
  timezone?: string | null
}

export interface TenderPreview {
  title: string | null
  reference_number: string | null
  deadline: string | null
  estimated_budget: number | null
  currency: string
  status: string
}

export interface SuggestedLink {
  url: string
  label: string
}

export interface SiteTestResult {
  count: number
  tenders: TenderPreview[]
  suggested_links: SuggestedLink[]
}

export async function listSites(): Promise<Site[]> {
  const { data } = await api.get<Site[]>('/api/sites')
  return data
}

export async function createSite(payload: SiteCreate): Promise<Site> {
  const { data } = await api.post<Site>('/api/sites', payload)
  return data
}

export async function updateSite(id: string, changes: Partial<Site>): Promise<Site> {
  const { data } = await api.patch<Site>(`/api/sites/${id}`, changes)
  return data
}

export async function deleteSite(id: string): Promise<void> {
  await api.delete(`/api/sites/${id}`)
}

export async function testSite(id: string): Promise<SiteTestResult> {
  const { data } = await api.post<SiteTestResult>(`/api/sites/${id}/test`)
  return data
}

export interface ScrapeRunResult {
  tenders_found: number
  errors: string[]
}

export async function scrapeSite(id: string): Promise<ScrapeRunResult> {
  const { data } = await api.post<ScrapeRunResult>(`/api/sites/${id}/scrape`)
  return data
}
