import type { LucideIcon } from 'lucide-react'
import type { ReactNode } from 'react'
import { cn } from '@/lib/utils'

export function PageHeader({
  title,
  description,
  icon: Icon,
  actions,
  className,
}: {
  title: string
  description?: string
  icon?: LucideIcon
  actions?: ReactNode
  className?: string
}) {
  return (
    <div
      className={cn(
        'rise-in relative overflow-hidden rounded-3xl border border-border/70 bg-[linear-gradient(135deg,var(--card),color-mix(in_oklch,var(--muted),var(--card)_54%))] p-5 shadow-sm shadow-slate-950/[0.04] sm:p-6',
        className,
      )}
    >
      <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-primary/35 to-transparent" />
      <div className="surface-glow pointer-events-none absolute -right-12 -top-16 h-36 w-36 rounded-full bg-primary/12 blur-3xl" />
      <div className="pointer-events-none absolute -bottom-20 left-1/4 h-36 w-36 rounded-full bg-accent/30 blur-3xl" />
      <div className="flex flex-wrap items-start justify-between gap-4">
      <div className="flex min-w-0 items-start gap-4">
        {Icon ? (
          <div className="flex size-12 shrink-0 items-center justify-center rounded-2xl bg-primary text-primary-foreground shadow-lg shadow-primary/15">
            <Icon className="size-5" />
          </div>
        ) : null}
        <div className="min-w-0">
          <h2 className="text-2xl font-semibold tracking-normal sm:text-3xl">{title}</h2>
          {description ? (
            <p className="mt-2 max-w-3xl text-sm leading-6 text-muted-foreground">
              {description}
            </p>
          ) : null}
        </div>
      </div>
      {actions ? <div className="flex shrink-0 flex-wrap items-center gap-2">{actions}</div> : null}
      </div>
    </div>
  )
}
