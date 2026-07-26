import type { LucideIcon } from 'lucide-react'
import type { ReactNode } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { cn } from '@/lib/utils'

export function SectionCard({
  title,
  description,
  icon: Icon,
  actions,
  children,
  className,
  contentClassName,
}: {
  title: string
  description?: string
  icon?: LucideIcon
  actions?: ReactNode
  children: ReactNode
  className?: string
  contentClassName?: string
}) {
  return (
    <Card
      className={cn(
        'rise-in gap-0 rounded-2xl border-border/70 bg-card/82 py-0 shadow-sm shadow-slate-950/[0.035] backdrop-blur-sm transition hover:-translate-y-0.5 hover:shadow-md hover:shadow-slate-950/[0.055]',
        className,
      )}
    >
      <CardHeader className="flex-row items-start justify-between gap-3 border-b border-border/60 px-4 py-4 sm:px-5">
        <div className="flex min-w-0 items-start gap-3">
          {Icon ? (
            <div className="flex size-9 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary ring-1 ring-primary/15">
              <Icon className="size-4" />
            </div>
          ) : null}
          <div className="min-w-0">
          <CardTitle className="text-sm font-semibold tracking-normal">
            {title}
          </CardTitle>
          {description ? <p className="mt-1 text-xs text-muted-foreground">{description}</p> : null}
          </div>
        </div>
        {actions ? <div className="flex shrink-0 items-center gap-2">{actions}</div> : null}
      </CardHeader>
      <CardContent className={cn('px-4 py-4 sm:px-5', contentClassName)}>{children}</CardContent>
    </Card>
  )
}
