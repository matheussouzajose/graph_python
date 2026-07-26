import type { ReactNode } from 'react'
import { useState } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import { Bell, Command, LogOut, Search, Sparkles } from 'lucide-react'
import { GlobalCommandMenu } from '@/components/layout/GlobalCommandMenu'
import { Sidebar } from '@/components/layout/Sidebar'
import { Button } from '@/components/ui/button'
import { useAuthUser, useSignOut } from '@/lib/auth-kit-core'
import { clearStoredAccessToken } from '@/lib/auth-token'
import { cn } from '@/lib/utils'
import type { AuthUser } from '@/types/api'

const PAGE_TITLES: Record<string, string> = {
  '/': 'Home',
  '/pedidos': 'Pedidos',
  '/produtos': 'Produtos',
  '/catalogo-produtos': 'Catálogo ERP',
  '/clientes': 'Clientes',
  '/recomendacoes': 'Recomendações',
  '/oraculo': 'Oráculo',
  '/agentes': 'Agentes',
  '/configuracoes': 'Configurações',
}

const PAGE_DESCRIPTIONS: Record<string, string> = {
  '/': 'Visão executiva, sincronização e processamento dos dados.',
  '/pedidos': 'Exploração, filtros e acompanhamento de pedidos sincronizados.',
  '/produtos': 'Rankings, associação e oportunidades de recomendação.',
  '/catalogo-produtos': 'Produtos brutos vindos da integração ERP.',
  '/clientes': 'Segmentação RFM, histórico e ações por cliente.',
  '/recomendacoes': 'Central para recomendações por produto ou cliente.',
  '/oraculo': 'Exploração analítica em linguagem natural.',
  '/agentes': 'Biblioteca e execução de assistentes de IA.',
  '/configuracoes': 'Perfil da empresa e gestão de integrações.',
}

const MOBILE_NAV = [
  { to: '/', label: 'Home' },
  { to: '/pedidos', label: 'Pedidos' },
  { to: '/produtos', label: 'Produtos' },
  { to: '/catalogo-produtos', label: 'Catálogo' },
  { to: '/clientes', label: 'Clientes' },
  { to: '/recomendacoes', label: 'Recomendações' },
  { to: '/oraculo', label: 'Oráculo' },
  { to: '/agentes', label: 'Agentes' },
  { to: '/configuracoes', label: 'Configurações' },
]

export function AppShell({ children }: { children: ReactNode }) {
  const location = useLocation()
  const authUser = useAuthUser<AuthUser>()
  const signOut = useSignOut('/login')
  const [commandOpen, setCommandOpen] = useState(false)
  const title = PAGE_TITLES[location.pathname] ?? 'Oráculo'
  const description = PAGE_DESCRIPTIONS[location.pathname]

  function logout() {
    clearStoredAccessToken()
    signOut()
  }

  return (
    <div className="flex min-h-svh bg-background text-foreground">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col md:pl-[17rem]">
        <header className="sticky top-0 z-20 border-b border-border/60 bg-background/78 backdrop-blur-xl">
          <div className="flex min-h-16 items-center gap-3 px-4 md:px-6">
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <h1 className="truncate text-sm font-semibold tracking-normal sm:text-base">{title}</h1>
                <span className="hidden rounded-full border border-emerald-200 bg-emerald-50 px-2 py-0.5 text-[11px] font-medium text-emerald-700 lg:inline-flex">
                  Operação ativa
                </span>
              </div>
              {description ? (
                <p className="hidden truncate text-xs text-muted-foreground sm:block">
                  {description}
                </p>
              ) : null}
            </div>

            <button
              type="button"
              className="ml-auto hidden min-w-[260px] max-w-md flex-1 items-center gap-2 rounded-2xl border border-border/70 bg-card/75 px-3 py-2 text-left text-sm text-muted-foreground shadow-sm shadow-slate-950/[0.03] transition hover:bg-card lg:flex"
              onClick={() => setCommandOpen(true)}
            >
              <Search className="size-4" />
              <span className="min-w-0 flex-1 truncate">Buscar clientes, produtos, pedidos...</span>
              <kbd className="rounded-md border bg-muted px-1.5 py-0.5 text-[10px] font-medium text-muted-foreground">
                ⌘K
              </kbd>
            </button>

            <Button variant="outline" size="icon" className="hidden rounded-xl bg-card/70 md:inline-flex">
              <Bell className="size-4" />
            </Button>

            <div className="hidden items-center gap-2 rounded-2xl border bg-card/75 p-1.5 pr-3 shadow-sm shadow-slate-950/[0.03] md:flex">
              <div className="flex size-8 items-center justify-center rounded-xl bg-primary text-primary-foreground">
                <Sparkles className="size-4" />
              </div>
              <div className="min-w-0">
                <p className="max-w-32 truncate text-xs font-medium">{authUser?.name ?? 'Usuário'}</p>
                <p className="max-w-32 truncate text-[11px] text-muted-foreground">{authUser?.role ?? 'user'}</p>
              </div>
            </div>

            <Button variant="ghost" size="icon" className="ml-auto rounded-xl md:hidden" onClick={logout}>
              <LogOut className="size-4" />
            </Button>

            <Button
              variant="ghost"
              size="icon"
              className="rounded-xl lg:hidden"
              onClick={() => setCommandOpen(true)}
            >
              <Command className="size-4" />
            </Button>
          </div>
        </header>
        <nav className="flex gap-1 overflow-x-auto border-b border-border/70 bg-background/80 px-2 py-2 backdrop-blur md:hidden">
          {MOBILE_NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === '/'}
              className={({ isActive }) =>
                cn(
                  'shrink-0 rounded-xl px-3 py-1.5 text-sm font-medium transition',
                  isActive
                    ? 'bg-foreground text-background shadow-sm'
                    : 'text-muted-foreground hover:bg-muted hover:text-foreground',
                )
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
        <main className="min-w-0 flex-1 px-4 py-5 md:px-6 md:py-6 lg:px-8">
          <div className="mx-auto w-full max-w-[1500px]">{children}</div>
        </main>
      </div>
      <GlobalCommandMenu open={commandOpen} onOpenChange={setCommandOpen} />
    </div>
  )
}
