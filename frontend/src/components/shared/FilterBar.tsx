import type { ReactNode } from 'react'
import { RotateCcw, X } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'

export interface FilterChip {
  key: string
  value: string
  label: string
}

export function FilterBar({
  title = 'Filtros',
  description,
  selected,
  onRemove,
  onClear,
  children,
}: {
  title?: string
  description?: string
  selected: FilterChip[]
  onRemove: (chip: FilterChip) => void
  onClear: () => void
  children: ReactNode
}) {
  return (
    <div className="space-y-3 rounded-2xl border border-border/70 bg-muted/25 p-3">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <p className="text-sm font-semibold">{title}</p>
            {selected.length > 0 ? <Badge variant="secondary">{selected.length}</Badge> : null}
          </div>
          {description ? <p className="mt-1 text-xs text-muted-foreground">{description}</p> : null}
        </div>
        {selected.length > 0 ? (
          <Button variant="outline" size="sm" className="rounded-xl" onClick={onClear}>
            <RotateCcw className="size-4" />
            Limpar
          </Button>
        ) : null}
      </div>

      <div className="flex flex-wrap items-center gap-2">{children}</div>

      {selected.length > 0 ? (
        <div className="flex flex-wrap gap-1.5 border-t border-border/60 pt-3">
          {selected.map((chip) => (
            <button
              key={`${chip.key}-${chip.value}`}
              type="button"
              onClick={() => onRemove(chip)}
              className="inline-flex max-w-full items-center gap-1 rounded-full border bg-card px-2.5 py-1 text-xs shadow-sm transition hover:bg-muted"
            >
              <span className="truncate">{chip.label}</span>
              <X className="size-3" />
            </button>
          ))}
        </div>
      ) : null}
    </div>
  )
}
