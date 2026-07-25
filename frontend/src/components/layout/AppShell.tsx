import type { ReactNode } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import { LogOut } from 'lucide-react'
import { Sidebar } from '@/components/layout/Sidebar'
import { Button } from '@/components/ui/button'
import { useSignOut } from '@/lib/auth-kit-core'
import { clearStoredAccessToken } from '@/lib/auth-token'
import { cn } from '@/lib/utils'

const PAGE_TITLES: Record<string, string> = {
  '/': 'Home',
  '/produtos': 'Produtos',
  '/clientes': 'Clientes',
  '/recomendacoes': 'Recomendações',
  '/oraculo': 'Oráculo',
  '/configuracoes': 'Configurações',
}

const PAGE_DESCRIPTIONS: Record<string, string> = {
  '/': 'Visão executiva, sincronização e processamento dos dados.',
  '/produtos': 'Rankings, associação e oportunidades de recomendação.',
  '/clientes': 'Segmentação RFM, histórico e ações por cliente.',
  '/recomendacoes': 'Central para recomendações por produto ou cliente.',
  '/oraculo': 'Exploração analítica em linguagem natural.',
  '/configuracoes': 'Perfil da empresa e gestão de integrações.',
}

const MOBILE_NAV = [
  { to: '/', label: 'Home' },
  { to: '/produtos', label: 'Produtos' },
  { to: '/clientes', label: 'Clientes' },
  { to: '/recomendacoes', label: 'Recomendações' },
  { to: '/oraculo', label: 'Oráculo' },
  { to: '/configuracoes', label: 'Configurações' },
]

export function AppShell({ children }: { children: ReactNode }) {
  const location = useLocation()
  const signOut = useSignOut()
  const title = PAGE_TITLES[location.pathname] ?? 'Oráculo'
  const description = PAGE_DESCRIPTIONS[location.pathname]

  function logout() {
    clearStoredAccessToken()
    signOut()
  }

  return (
    <div className="flex min-h-svh bg-background">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col md:pl-64">
        <header className="sticky top-0 z-10 flex h-16 items-center border-b bg-background/92 px-4 backdrop-blur md:px-6">
          <div className="min-w-0">
            <h1 className="text-base font-semibold tracking-tight">{title}</h1>
            {description ? (
              <p className="hidden truncate text-xs text-muted-foreground sm:block">
                {description}
              </p>
            ) : null}
          </div>
          <Button variant="ghost" size="icon" className="ml-auto md:hidden" onClick={logout}>
            <LogOut className="size-4" />
          </Button>
        </header>
        <nav className="flex gap-1 overflow-x-auto border-b bg-background px-2 py-1.5 md:hidden">
          {MOBILE_NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === '/'}
              className={({ isActive }) =>
                cn(
                  'shrink-0 rounded-md px-3 py-1.5 text-sm font-medium',
                  isActive ? 'bg-primary text-primary-foreground' : 'text-muted-foreground',
                )
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
        <main className="min-w-0 flex-1 p-4 md:p-6">{children}</main>
      </div>
    </div>
  )
}
