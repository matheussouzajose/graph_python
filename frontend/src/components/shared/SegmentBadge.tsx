import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'

const SEGMENT_LABELS: Record<string, string> = {
  campeoes: 'Campeões',
  leais: 'Leais',
  novos: 'Novos',
  em_risco: 'Em risco',
  hibernando: 'Hibernando',
  potencial: 'Potencial',
}

const SEGMENT_STYLES: Record<string, string> = {
  campeoes: 'border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-900 dark:bg-emerald-950 dark:text-emerald-400',
  leais: 'border-blue-200 bg-blue-50 text-blue-700 dark:border-blue-900 dark:bg-blue-950 dark:text-blue-400',
  novos: 'border-violet-200 bg-violet-50 text-violet-700 dark:border-violet-900 dark:bg-violet-950 dark:text-violet-400',
  em_risco: 'border-amber-200 bg-amber-50 text-amber-700 dark:border-amber-900 dark:bg-amber-950 dark:text-amber-400',
  hibernando: 'border-slate-200 bg-slate-100 text-slate-700 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-400',
  potencial: 'border-cyan-200 bg-cyan-50 text-cyan-700 dark:border-cyan-900 dark:bg-cyan-950 dark:text-cyan-400',
}

export function SegmentBadge({ segment }: { segment: string | null | undefined }) {
  if (!segment) return <span className="text-muted-foreground">—</span>
  return (
    <Badge
      variant="outline"
      className={cn('font-medium', SEGMENT_STYLES[segment] ?? 'text-muted-foreground')}
    >
      {SEGMENT_LABELS[segment] ?? segment}
    </Badge>
  )
}
