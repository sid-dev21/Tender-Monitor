/** Extract a human-readable message from an axios/FastAPI error.
 *
 * FastAPI returns `detail` as a STRING for HTTPException (e.g. "Email already
 * registered") but as an ARRAY of error objects for request-body validation
 * (each { type, loc, msg, ... }). This normalizes both to a single string so we
 * never try to render an object as a React child.
 */
export function errorMessage(err: unknown, fallback: string): string {
  const detail = (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail

  if (typeof detail === 'string') return detail

  if (Array.isArray(detail)) {
    const msgs = detail
      .map((d) => (typeof d === 'object' && d && 'msg' in d ? String((d as { msg: unknown }).msg) : null))
      .filter(Boolean)
    if (msgs.length) return msgs.join(' · ')
  }

  return fallback
}
