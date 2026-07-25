import { Badge } from '@/components/ui/badge'
import type { RecommendationReason } from '@/types/api'

const REASON_LABELS: Record<string, string> = {
  similaridade: 'Similaridade',
  comprado_junto: 'Comprado junto',
  similar_ao_historico: 'Similar ao histórico',
  comprado_junto_ao_historico: 'Comprado junto (histórico)',
}

export function ReasonBadges({ reasons }: { reasons: RecommendationReason[] }) {
  if (!reasons.length) return <span className="text-muted-foreground">—</span>
  return (
    <div className="flex flex-wrap gap-1">
      {reasons.map((reason) => (
        <Badge key={reason} variant="secondary" className="font-normal">
          {REASON_LABELS[reason] ?? reason}
        </Badge>
      ))}
    </div>
  )
}
