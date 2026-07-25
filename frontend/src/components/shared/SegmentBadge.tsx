import { Badge } from '@/components/ui/badge'
import { getSegmentColor, getSegmentLabel } from '@/lib/segments'
import { cn } from '@/lib/utils'

export function SegmentBadge({ segment }: { segment: string | null | undefined }) {
  if (!segment) return <span className="text-muted-foreground">—</span>
  const color = getSegmentColor(segment)
  return (
    <Badge
      variant="outline"
      className={cn('h-6 rounded-md px-2 font-medium', color?.badge ?? 'text-muted-foreground')}
    >
      {getSegmentLabel(segment)}
    </Badge>
  )
}
