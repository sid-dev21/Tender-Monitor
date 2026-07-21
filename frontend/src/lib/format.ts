/** Shared, locale-aware formatting used across pages. UI is French. */

export function fmtDate(iso: string | null | undefined): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('fr-FR', { day: '2-digit', month: 'long', year: 'numeric' })
}

export function fmtDateShort(iso: string | null | undefined): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('fr-FR', { day: '2-digit', month: 'short', year: 'numeric' })
}

export function fmtMoney(amount: number | null | undefined, currency = 'FCFA'): string {
  if (amount == null) return '—'
  return `${amount.toLocaleString('fr-FR')} ${currency}`
}

/** Whole days until a deadline (negative when past). null if no deadline. */
export function daysLeft(iso: string | null | undefined): number | null {
  if (!iso) return null
  return Math.ceil((new Date(iso).getTime() - Date.now()) / 86_400_000)
}

export type DeadlineTone = 'urgent' | 'soon' | 'ok' | 'expired' | 'none'

export function deadlineLabel(iso: string | null | undefined): { text: string; tone: DeadlineTone } {
  const d = daysLeft(iso)
  if (d == null) return { text: '—', tone: 'none' }
  if (d < 0) return { text: 'Expiré', tone: 'expired' }
  if (d === 0) return { text: "Aujourd'hui", tone: 'urgent' }
  if (d === 1) return { text: 'Demain', tone: 'urgent' }
  if (d <= 3) return { text: `Dans ${d} jours`, tone: 'urgent' }
  if (d <= 7) return { text: `${d} jours`, tone: 'soon' }
  return { text: `${d} jours`, tone: 'ok' }
}

/** "il y a 12 min" / "il y a 3 h" / "il y a 2 j". */
export function relativeTime(iso: string | null | undefined): string {
  if (!iso) return ''
  const diff = Date.now() - new Date(iso).getTime()
  const min = Math.round(diff / 60_000)
  if (min < 1) return "à l'instant"
  if (min < 60) return `il y a ${min} min`
  const h = Math.round(min / 60)
  if (h < 24) return `il y a ${h} h`
  const j = Math.round(h / 24)
  return `il y a ${j} j`
}

/** Domain of a URL, for compact provenance. */
export function hostOf(url: string | null | undefined): string {
  if (!url) return ''
  try {
    return new URL(url).hostname.replace(/^www\./, '')
  } catch {
    return url
  }
}

export function todayLong(): string {
  const s = new Date().toLocaleDateString('fr-FR', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  })
  return s.charAt(0).toUpperCase() + s.slice(1)
}
