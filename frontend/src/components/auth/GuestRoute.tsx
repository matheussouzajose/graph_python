import type { ReactNode } from 'react'
import { Navigate } from 'react-router-dom'
import { useIsAuthenticated } from '@/lib/auth-kit-core'

export function GuestRoute({ children }: { children: ReactNode }) {
  const isAuthenticated = useIsAuthenticated()

  if (isAuthenticated) {
    return <Navigate to="/" replace />
  }

  return children
}
