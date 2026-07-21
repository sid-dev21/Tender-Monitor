/** Presentation helpers derived from the account email (backend has no name field). */

/** "b.ouedraogo@x.bf" → "B Ouedraogo"; falls back to the raw local part. */
export function displayName(email?: string | null): string {
  if (!email) return 'Mon compte'
  const local = email.split('@')[0]
  const words = local
    .split(/[.\-_+]|\d+/)
    .filter(Boolean)
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
  return words.length ? words.join(' ') : local
}

/** First letters of up to two words, uppercased. */
export function initials(name: string): string {
  const parts = name.split(/\s+/).filter(Boolean)
  const letters = parts.slice(0, 2).map((w) => w[0])
  return (letters.join('') || name.slice(0, 2)).toUpperCase()
}
