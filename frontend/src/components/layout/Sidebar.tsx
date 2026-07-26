import { useState } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import {
  Bot,
  ChevronDown,
  Compass,
  Settings,
  LayoutDashboard,
  LogOut,
  Package,
  ShoppingCart,
  Sparkles,
  Users,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { useAuthUser, useSignOut } from '@/lib/auth-kit-core'
import { clearStoredAccessToken } from '@/lib/auth-token'
import type { AuthUser } from '@/types/api'

const NAV_ITEMS = [
  { to: '/', label: 'Home', icon: LayoutDashboard, end: true },
  { to: '/pedidos', label: 'Pedidos', icon: ShoppingCart, end: false },
  { to: '/produtos', label: 'Produtos', icon: Package, end: false },
  { to: '/clientes', label: 'Clientes', icon: Users, end: false },
  { to: '/recomendacoes', label: 'Recomendações', icon: Sparkles, end: false },
  { to: '/oraculo', label: 'Oráculo', icon: Compass, end: false },
] as const

const STANDALONE_NAV_ITEMS = [
  { to: '/catalogo-produtos', label: 'Catálogo ERP', icon: Package, end: false },
  { to: '/agentes', label: 'Agentes', icon: Bot, end: false },
] as const

const SECONDARY_NAV_ITEMS = [
  { to: '/configuracoes', label: 'Configurações', icon: Settings, end: false },
] as const

export function Sidebar() {
  const authUser = useAuthUser<AuthUser>()
  const signOut = useSignOut('/login')
  const location = useLocation()
  const [salesOpen, setSalesOpen] = useState(true)
  const salesActive = NAV_ITEMS.some((item) =>
    item.end ? location.pathname === item.to : location.pathname.startsWith(item.to),
  )

  function logout() {
    clearStoredAccessToken()
    signOut()
  }

  return (
    <aside className="fixed inset-y-0 left-0 z-30 hidden w-[17rem] border-r border-sidebar-border bg-sidebar text-sidebar-foreground md:flex md:flex-col">
      <div className="flex h-20 shrink-0 items-center gap-3 px-4">
        <div className="flex size-11 items-center justify-center rounded-2xl bg-sidebar-primary text-sidebar-primary-foreground shadow-lg shadow-black/20">
          <Sparkles className="size-4" />
        </div>
        <div className="min-w-0">
          <span className="block text-sm font-semibold tracking-normal">Oráculo</span>
          <span className="block truncate text-xs text-sidebar-foreground/55">
            Inteligência comercial
          </span>
        </div>
      </div>
      <nav className="min-h-0 flex-1 overflow-y-auto px-3 pb-3">
        <div className="mb-3 rounded-2xl border border-sidebar-border bg-white/[0.045] p-3">
          <div className="flex items-center justify-between gap-3">
            <div className="min-w-0">
              <p className="truncate text-xs font-medium text-sidebar-foreground/72">Pipeline</p>
              <p className="mt-0.5 truncate text-[11px] text-sidebar-foreground/45">Pedidos e sinais atualizados</p>
            </div>
            <span className="size-2.5 rounded-full bg-emerald-400 shadow-[0_0_18px_rgba(52,211,153,0.8)]" />
          </div>
        </div>

        <div className="space-y-1.5">
          <button
            type="button"
            onClick={() => setSalesOpen((open) => !open)}
            className={cn(
              'flex w-full items-center gap-2.5 rounded-xl px-3 py-2.5 text-left text-sm font-medium transition',
              salesActive
                ? 'bg-white/[0.09] text-sidebar-accent-foreground'
                : 'text-sidebar-foreground/66 hover:bg-white/[0.07] hover:text-sidebar-accent-foreground',
            )}
          >
            <ShoppingCart className="size-4" />
            <span className="min-w-0 flex-1">Vendas</span>
            <ChevronDown
              className={cn(
                'size-4 text-sidebar-foreground/55 transition-transform',
                salesOpen && 'rotate-180',
              )}
            />
          </button>

          {salesOpen ? (
            <div className="ml-4 space-y-1 border-l border-sidebar-border/70 pl-3">
              {NAV_ITEMS.map(({ to, label, icon: Icon, end }) => (
                <NavLink
                  key={to}
                  to={to}
                  end={end}
                  className={({ isActive }) =>
                    cn(
                      'group flex items-center gap-2.5 rounded-xl px-3 py-2 text-sm font-medium transition',
                      isActive
                        ? 'bg-sidebar-primary text-sidebar-primary-foreground shadow-lg shadow-black/15'
                        : 'text-sidebar-foreground/64 hover:bg-white/[0.07] hover:text-sidebar-accent-foreground',
                    )
                  }
                >
                  <Icon className="size-4 opacity-85 transition group-hover:opacity-100" />
                  <span className="truncate">{label}</span>
                </NavLink>
              ))}
            </div>
          ) : null}

          <div className="space-y-1 pt-2">
            {STANDALONE_NAV_ITEMS.map(({ to, label, icon: Icon, end }) => (
              <NavLink
                key={to}
                to={to}
                end={end}
                className={({ isActive }) =>
                  cn(
                    'group flex items-center gap-2.5 rounded-xl px-3 py-2.5 text-sm font-medium transition',
                    isActive
                      ? 'bg-sidebar-primary text-sidebar-primary-foreground shadow-lg shadow-black/15'
                      : 'text-sidebar-foreground/64 hover:bg-white/[0.07] hover:text-sidebar-accent-foreground',
                  )
                }
              >
                <Icon className="size-4 opacity-85 transition group-hover:opacity-100" />
                <span className="truncate">{label}</span>
              </NavLink>
            ))}
          </div>

          <div className="pt-2">
            {SECONDARY_NAV_ITEMS.map(({ to, label, icon: Icon, end }) => (
              <NavLink
                key={to}
                to={to}
                end={end}
                className={({ isActive }) =>
                  cn(
                    'group flex items-center gap-2.5 rounded-xl px-3 py-2.5 text-sm font-medium transition',
                    isActive
                      ? 'bg-sidebar-primary text-sidebar-primary-foreground shadow-lg shadow-black/15'
                      : 'text-sidebar-foreground/64 hover:bg-white/[0.07] hover:text-sidebar-accent-foreground',
                  )
                }
              >
                <Icon className="size-4 opacity-85 transition group-hover:opacity-100" />
                <span className="truncate">{label}</span>
              </NavLink>
            ))}
          </div>
        </div>
      </nav>
      <div className="shrink-0 p-3">
        <div className="space-y-3 rounded-2xl border border-sidebar-border bg-white/[0.045] p-3">
          <div className="min-w-0 text-xs">
            <p className="truncate font-medium text-sidebar-foreground">{authUser?.name}</p>
            <p className="truncate text-sidebar-foreground/55">{authUser?.email}</p>
          </div>
          <Button
            variant="outline"
            size="sm"
            className="w-full justify-start rounded-xl border-sidebar-border bg-transparent text-sidebar-foreground hover:bg-white/[0.07]"
            onClick={logout}
          >
            <LogOut className="size-4" />
            Sair
          </Button>
        </div>
      </div>
    </aside>
  )
}
