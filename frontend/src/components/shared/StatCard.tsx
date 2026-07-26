import type { LucideIcon } from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { cn } from '@/lib/utils'

interface StatCardProps {
  label: string
  value: string
  icon: LucideIcon
  hint?: string
  loading?: boolean
  className?: string
  tone?: 'teal' | 'blue' | 'amber' | 'violet' | 'rose'
}

const TONES = {
  teal: 'bg-teal-500 text-white shadow-teal-500/20',
  blue: 'bg-blue-500 text-white shadow-blue-500/20',
  amber:
    'bg-amber-400 text-slate-950 shadow-amber-400/20',
  violet:
    'bg-violet-500 text-white shadow-violet-500/20',
  rose: 'bg-rose-500 text-white shadow-rose-500/20',
}

export function StatCard({
  label,
  value,
  icon: Icon,
  hint,
  loading,
  className,
  tone = 'teal',
}: StatCardProps) {
  return (
    <Card
      className={cn(
        'relative gap-0 overflow-hidden rounded-2xl border-border/70 bg-card/86 py-4 shadow-sm shadow-slate-950/[0.035] transition hover:-translate-y-0.5 hover:shadow-md',
        className,
      )}
    >
      <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-foreground/12 to-transparent" />
      <CardContent className="flex items-start justify-between gap-3 px-4">
        <div className="min-w-0">
          <p className="text-xs font-medium uppercase tracking-[0.08em] text-muted-foreground">{label}</p>
          {loading ? (
            <Skeleton className="mt-2 h-7 w-24" />
          ) : (
            <p className="mt-2 truncate text-2xl font-semibold tracking-normal" title={value}>
              {value}
            </p>
          )}
          {hint ? <p className="mt-1 text-xs text-muted-foreground">{hint}</p> : null}
        </div>
        <div
          className={cn(
            'flex size-10 shrink-0 items-center justify-center rounded-2xl shadow-lg',
            TONES[tone],
          )}
        >
          <Icon className="size-4.5" />
        </div>
      </CardContent>
    </Card>
  )
}
