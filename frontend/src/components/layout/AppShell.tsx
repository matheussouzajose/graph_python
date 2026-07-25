import type { ReactNode } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import { Sidebar } from '@/components/layout/Sidebar'
import { cn } from '@/lib/utils'

const PAGE_TITLES: Record<string, string> = {
  '/': 'Home',
  '/produtos': 'Produtos',
  '/clientes': 'Clientes',
  '/recomendacoes': 'Recomendações',
  '/oraculo': 'Oráculo',
}

const MOBILE_NAV = [
  { to: '/', label: 'Home' },
  { to: '/produtos', label: 'Produtos' },
  { to: '/clientes', label: 'Clientes' },
  { to: '/recomendacoes', label: 'Recomendações' },
  { to: '/oraculo', label: 'Oráculo' },
]

export function AppShell({ children }: { children: ReactNode }) {
  const location = useLocation()
  const title = PAGE_TITLES[location.pathname] ?? 'Oráculo'

  return (
    <div className="flex min-h-svh bg-muted/30">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-10 flex h-14 items-center border-b bg-background px-4 md:px-6">
          <h1 className="text-base font-semibold tracking-tight">{title}</h1>
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
