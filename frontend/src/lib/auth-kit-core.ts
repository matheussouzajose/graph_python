import useAuthUserModule from 'react-auth-kit/hooks/useAuthUser'
import useIsAuthenticatedModule from 'react-auth-kit/hooks/useIsAuthenticated'
import useSignInModule from 'react-auth-kit/hooks/useSignIn'
import useSignOutModule from 'react-auth-kit/hooks/useSignOut'
import ReactRouterPluginModule from '@auth-kit/react-router/route'

type WrappedDefault<T> = T | { default: T | { default: T } }

export function unwrapDefault<T>(value: WrappedDefault<T>): T {
  const first =
    typeof value === 'object' && value !== null && 'default' in value ? value.default : value
  return (typeof first === 'object' && first !== null && 'default' in first
    ? first.default
    : first) as T
}

type SignInConfig<T> = {
  auth: {
    token: string
    type?: string
  }
  refresh?: string | null
  userState?: T
  navigateTo?: string
}

type UseSignIn = <T>() => (signInConfig: SignInConfig<T>) => boolean
type UseSignOut = (navigateTo?: string) => () => void
type UseAuthUser = <T>() => T | null
type UseIsAuthenticated = () => boolean

export const ReactRouterPlugin = unwrapDefault<object>(
  ReactRouterPluginModule as unknown as WrappedDefault<object>,
)

export const useSignIn = unwrapDefault<UseSignIn>(
  useSignInModule as unknown as WrappedDefault<UseSignIn>,
)

export const useSignOut = unwrapDefault<UseSignOut>(
  useSignOutModule as unknown as WrappedDefault<UseSignOut>,
)

export const useAuthUser = unwrapDefault<UseAuthUser>(
  useAuthUserModule as unknown as WrappedDefault<UseAuthUser>,
)

export const useIsAuthenticated = unwrapDefault<UseIsAuthenticated>(
  useIsAuthenticatedModule as unknown as WrappedDefault<UseIsAuthenticated>,
)
