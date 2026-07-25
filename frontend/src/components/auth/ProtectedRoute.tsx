import type { ReactNode } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { useIsAuthenticated } from '@/lib/auth-kit-core'
import { clearStoredAccessToken } from '@/lib/auth-token'

export function ProtectedRoute({ children }: { children: ReactNode }) {
  const location = useLocation()
  const isAuthenticated = useIsAuthenticated()

  if (!isAuthenticated) {
    clearStoredAccessToken()
    return <Navigate to="/login" replace state={{ from: location }} />
  }

  return children
}
