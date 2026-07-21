/** Single source of truth for JWT storage.
 *
 * "Remember me" keeps tokens in localStorage (survives browser restart);
 * otherwise sessionStorage (cleared when the tab closes). Both the request
 * interceptor and the auth context read/write through here.
 */
const ACCESS = 'access_token'
const REFRESH = 'refresh_token'

function storeHoldingTokens(): Storage | null {
  if (localStorage.getItem(REFRESH)) return localStorage
  if (sessionStorage.getItem(REFRESH)) return sessionStorage
  return null
}

export function getAccessToken(): string | null {
  return localStorage.getItem(ACCESS) ?? sessionStorage.getItem(ACCESS)
}

export function getRefreshToken(): string | null {
  return localStorage.getItem(REFRESH) ?? sessionStorage.getItem(REFRESH)
}

export function setTokens(access: string, refresh: string, remember?: boolean): void {
  // remember === undefined => keep tokens in whichever store already holds them
  // (used by the silent refresh, which must not move them between stores).
  const store =
    remember === undefined
      ? (storeHoldingTokens() ?? sessionStorage)
      : remember
        ? localStorage
        : sessionStorage
  store.setItem(ACCESS, access)
  store.setItem(REFRESH, refresh)
}

export function clearTokens(): void {
  for (const store of [localStorage, sessionStorage]) {
    store.removeItem(ACCESS)
    store.removeItem(REFRESH)
  }
}
