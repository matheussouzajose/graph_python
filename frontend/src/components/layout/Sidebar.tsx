import { useState } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import {
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

const SECONDARY_NAV_ITEMS = [
  { to: '/configuracoes', label: 'Configurações', icon: Settings, end: false },
] as const

export function Sidebar() {
  const authUser = useAuthUser<AuthUser>()
  const signOut = useSignOut()
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
    <aside className="fixed inset-y-0 left-0 z-30 hidden w-64 border-r border-sidebar-border bg-sidebar text-sidebar-foreground md:flex md:flex-col">
      <div className="flex h-16 shrink-0 items-center gap-3 border-b border-sidebar-border px-5">
        <div className="flex size-9 items-center justify-center rounded-lg bg-sidebar-primary text-sidebar-primary-foreground shadow-sm">
          <Sparkles className="size-4" />
        </div>
        <div className="min-w-0">
          <span className="block text-sm font-semibold tracking-tight">Oráculo</span>
          <span className="block truncate text-xs text-sidebar-foreground/55">
            Inteligência comercial
          </span>
        </div>
      </div>
      <nav className="min-h-0 flex-1 overflow-y-auto p-3">
        <div className="space-y-1.5">
          <button
            type="button"
            onClick={() => setSalesOpen((open) => !open)}
            className={cn(
              'flex w-full items-center gap-2.5 rounded-lg px-3 py-2.5 text-left text-sm font-medium transition-colors',
              salesActive
                ? 'bg-sidebar-accent text-sidebar-accent-foreground'
                : 'text-sidebar-foreground/68 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground',
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
            <div className="space-y-1 border-l border-sidebar-border/70 pl-3 ml-4">
              {NAV_ITEMS.map(({ to, label, icon: Icon, end }) => (
                <NavLink
                  key={to}
                  to={to}
                  end={end}
                  className={({ isActive }) =>
                    cn(
                      'flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                      isActive
                        ? 'bg-sidebar-primary text-sidebar-primary-foreground shadow-sm'
                        : 'text-sidebar-foreground/68 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground',
                    )
                  }
                >
                  <Icon className="size-4" />
                  {label}
                </NavLink>
              ))}
            </div>
          ) : null}

          <div className="pt-2">
            {SECONDARY_NAV_ITEMS.map(({ to, label, icon: Icon, end }) => (
              <NavLink
                key={to}
                to={to}
                end={end}
                className={({ isActive }) =>
                  cn(
                    'flex items-center gap-2.5 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors',
                    isActive
                      ? 'bg-sidebar-primary text-sidebar-primary-foreground shadow-sm'
                      : 'text-sidebar-foreground/68 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground',
                  )
                }
              >
                <Icon className="size-4" />
                {label}
              </NavLink>
            ))}
          </div>
        </div>
      </nav>
      <div className="shrink-0 space-y-3 border-t border-sidebar-border p-3">
        <div className="min-w-0 text-xs">
          <p className="truncate font-medium text-sidebar-foreground">{authUser?.name}</p>
          <p className="truncate text-sidebar-foreground/55">{authUser?.email}</p>
        </div>
        <Button
          variant="outline"
          size="sm"
          className="w-full justify-start border-sidebar-border bg-transparent text-sidebar-foreground hover:bg-sidebar-accent"
          onClick={logout}
        >
          <LogOut className="size-4" />
          Sair
        </Button>
      </div>
    </aside>
  )
}
