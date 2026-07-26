import type { LucideIcon } from 'lucide-react'
import type { ReactNode } from 'react'
import { Inbox } from 'lucide-react'

interface EmptyStateProps {
  title: string
  description?: string
  icon?: LucideIcon
  action?: ReactNode
}

export function EmptyState({ title, description, icon: Icon = Inbox, action }: EmptyStateProps) {
  return (
    <div className="rise-in relative flex flex-col items-center justify-center gap-3 overflow-hidden rounded-3xl border border-dashed border-border/80 bg-muted/20 px-4 py-12 text-center">
      <div className="surface-glow pointer-events-none absolute right-1/4 top-0 h-24 w-24 rounded-full bg-primary/10 blur-2xl" />
      <div className="relative flex size-12 items-center justify-center rounded-2xl bg-card text-primary shadow-sm ring-1 ring-border/70">
        <Icon className="size-6" />
      </div>
      <p className="relative text-sm font-semibold">{title}</p>
      {description ? (
        <p className="relative max-w-sm text-xs leading-5 text-muted-foreground">{description}</p>
      ) : null}
      {action ? <div className="relative mt-1">{action}</div> : null}
    </div>
  )
}
