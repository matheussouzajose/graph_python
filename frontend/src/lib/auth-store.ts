import createAuthStoreModule from 'react-auth-kit/store/createAuthStore'
import type { AuthUser } from '@/types/api'

type CreateAuthStore = typeof import('react-auth-kit/store/createAuthStore').default

const createAuthStore = (
  typeof createAuthStoreModule === 'function'
    ? createAuthStoreModule
    : (createAuthStoreModule as unknown as { default: CreateAuthStore }).default
) as CreateAuthStore

export const authStore = createAuthStore<AuthUser>('localstorage', {
  authName: '_oraculo_auth',
})
