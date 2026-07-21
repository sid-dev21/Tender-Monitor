import { Navigate, Outlet } from 'react-router-dom'
import { useAuth } from '../lib/auth'

/** Gates the authenticated area: redirects to /login when there's no valid session. */
export function ProtectedRoute() {
  const { isAuthenticated, isLoading } = useAuth()

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-cream">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-line border-t-orange" />
      </div>
    )
  }

  if (!isAuthenticated) return <Navigate to="/login" replace />

  return <Outlet />
}
