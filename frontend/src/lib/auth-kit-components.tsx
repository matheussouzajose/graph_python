import type { ComponentType, ReactNode } from 'react'
import AuthProviderModule from 'react-auth-kit/AuthProvider'
import { unwrapDefault } from '@/lib/auth-kit-core'

type WrappedDefault<T> = T | { default: T | { default: T } }

type AuthProviderProps = {
  store: unknown
  router?: unknown
  fallbackPath?: string
  children: ReactNode
}

const RawAuthProvider = unwrapDefault<ComponentType<AuthProviderProps>>(
  AuthProviderModule as unknown as WrappedDefault<ComponentType<AuthProviderProps>>,
)

export function AuthProvider(props: AuthProviderProps) {
  return <RawAuthProvider {...props} />
}
