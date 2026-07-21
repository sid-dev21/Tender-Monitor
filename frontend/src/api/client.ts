import axios from 'axios'
import { clearTokens, getAccessToken, getRefreshToken, setTokens } from '../lib/tokens'

// The one axios instance the whole app uses. Its base URL supports the three
// ways this app gets deployed:
//
//   1. VITE_API_URL set  -> use it. Split deployment: the SPA is on Vercel and
//      the API lives on another host.
//   2. production build, no VITE_API_URL -> same origin (''), i.e. relative
//      requests. Single-origin deployment, where FastAPI itself serves
//      frontend/dist (see backend/app/main.py). Works behind any hostname —
//      including a tunnel URL that changes on every restart — with no rebuild.
//   3. dev -> the local backend on its own port, since Vite serves the SPA.
const configuredApiUrl = import.meta.env.VITE_API_URL?.trim()
const baseURL = configuredApiUrl || (import.meta.env.PROD ? '' : 'http://localhost:8000')

export const api = axios.create({
  baseURL,
  headers: { 'Content-Type': 'application/json' },
})

// Attach the JWT access token to every outgoing request.
api.interceptors.request.use((config) => {
  const token = getAccessToken()
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// --- Silent refresh on 401 -------------------------------------------------
// The access token lives 15 minutes. When it expires, one request refreshes it
// using the refresh token; concurrent 401s share that single refresh (single-
// flight). If refresh fails, tokens are cleared and the user goes to /login.
let refreshInFlight: Promise<string | null> | null = null

async function refreshAccessToken(): Promise<string | null> {
  const refresh = getRefreshToken()
  if (!refresh) return null
  try {
    // Bare axios (not `api`) so this call skips the interceptors — no recursion.
    const { data } = await axios.post(`${baseURL}/api/auth/refresh`, {
      refresh_token: refresh,
    })
    setTokens(data.access_token, data.refresh_token)
    return data.access_token as string
  } catch {
    clearTokens()
    return null
  }
}

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config
    const status = error.response?.status

    if (status === 401 && original && !original._retry) {
      original._retry = true
      refreshInFlight = refreshInFlight ?? refreshAccessToken()
      const newToken = await refreshInFlight
      refreshInFlight = null

      if (newToken) {
        original.headers.Authorization = `Bearer ${newToken}`
        return api(original) // replay the original request with the fresh token
      }

      // Refresh failed / no refresh token — send them to login.
      if (window.location.pathname !== '/login') {
        window.location.assign('/login')
      }
    }

    return Promise.reject(error)
  },
)
