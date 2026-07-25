import type { ColumnDef } from '@tanstack/react-table'
import { DataTable } from '@/components/shared/DataTable'
import { ReasonBadges } from '@/components/shared/ReasonBadges'
import { formatDecimal, formatNumber } from '@/lib/format'
import type { RecommendationResult } from '@/types/api'

const columns: ColumnDef<RecommendationResult, any>[] = [
  {
    accessorKey: 'product_name',
    header: 'Produto',
    cell: ({ row }) => (
      <div>
        <p className="font-medium">{row.original.product_name ?? '—'}</p>
        <p className="text-xs text-muted-foreground">Código {row.original.product_code ?? '—'}</p>
      </div>
    ),
  },
  {
    accessorKey: 'score',
    header: 'Score',
    cell: ({ getValue }) => (
      <span className="font-mono text-sm font-medium">{formatDecimal(getValue<number>(), 3)}</span>
    ),
  },
  {
    accessorKey: 'reasons',
    header: 'Motivo',
    enableSorting: false,
    cell: ({ getValue }) => <ReasonBadges reasons={getValue<string[]>()} />,
  },
  {
    accessorKey: 'similarity_score',
    header: 'Similaridade',
    cell: ({ getValue }) => formatDecimal(getValue<number>(), 3),
  },
  {
    accessorKey: 'lift',
    header: 'Lift',
    cell: ({ getValue }) => formatDecimal(getValue<number>(), 2),
  },
  {
    accessorKey: 'confidence',
    header: 'Confiança',
    cell: ({ getValue }) => formatDecimal(getValue<number>(), 2),
  },
  {
    accessorKey: 'support_count',
    header: 'Suporte',
    cell: ({ getValue }) => formatNumber(getValue<number>()),
  },
  {
    accessorKey: 'pagerank',
    header: 'PageRank',
    cell: ({ getValue }) => {
      const value = getValue<number | null>()
      return value === null ? '—' : formatDecimal(value, 4)
    },
  },
]

interface RecommendationResultsTableProps {
  results: RecommendationResult[] | undefined
  loading?: boolean
  emptyDescription?: string
}

export function RecommendationResultsTable({
  results,
  loading,
  emptyDescription,
}: RecommendationResultsTableProps) {
  return (
    <DataTable
      columns={columns}
      data={results}
      loading={loading}
      emptyTitle="Nenhuma recomendação encontrada"
      emptyDescription={
        emptyDescription ??
        'Rode POST /graph-algorithms/run pelo menos uma vez para gerar similaridade e regras de associação.'
      }
      getRowId={(row) => row.product_id}
    />
  )
}
