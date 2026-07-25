import { Badge } from '@/components/ui/badge'
import type { RecommendationReason } from '@/types/api'

const REASON_LABELS: Record<string, string> = {
  similaridade: 'Similaridade',
  comprado_junto: 'Comprado junto',
  similar_ao_historico: 'Similar ao histórico',
  comprado_junto_ao_historico: 'Comprado junto (histórico)',
}

const REASON_STYLES: Record<string, string> = {
  similaridade: 'bg-blue-50 text-blue-700 border-blue-200 dark:bg-blue-950 dark:text-blue-300 dark:border-blue-900',
  comprado_junto:
    'bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-950 dark:text-emerald-300 dark:border-emerald-900',
  similar_ao_historico:
    'bg-violet-50 text-violet-700 border-violet-200 dark:bg-violet-950 dark:text-violet-300 dark:border-violet-900',
  comprado_junto_ao_historico:
    'bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-950 dark:text-amber-300 dark:border-amber-900',
}

export function ReasonBadges({ reasons }: { reasons: RecommendationReason[] }) {
  if (!reasons.length) return <span className="text-muted-foreground">—</span>
  return (
    <div className="flex flex-wrap gap-1">
      {reasons.map((reason) => (
        <Badge
          key={reason}
          variant="outline"
          className={REASON_STYLES[reason] ?? 'font-normal'}
        >
          {REASON_LABELS[reason] ?? reason}
        </Badge>
      ))}
    </div>
  )
}
