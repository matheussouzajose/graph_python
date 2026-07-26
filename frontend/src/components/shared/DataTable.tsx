import {
  type ColumnDef,
  type SortingState,
  flexRender,
  getCoreRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  useReactTable,
} from '@tanstack/react-table'
import { ArrowDown, ArrowUp, ArrowUpDown, Rows3, Search, StretchHorizontal } from 'lucide-react'
import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Skeleton } from '@/components/ui/skeleton'
import { EmptyState } from '@/components/shared/EmptyState'
import { cn } from '@/lib/utils'

interface DataTableProps<TData> {
  columns: ColumnDef<TData, any>[]
  data: TData[] | undefined
  loading?: boolean
  emptyTitle?: string
  emptyDescription?: string
  getRowId?: (row: TData) => string
  onRowClick?: (row: TData) => void
  searchPlaceholder?: string
  searchable?: boolean
  pageSize?: number
}

export function DataTable<TData>({
  columns,
  data,
  loading,
  emptyTitle = 'Nenhum dado encontrado',
  emptyDescription,
  getRowId,
  onRowClick,
  searchPlaceholder = 'Buscar...',
  searchable = false,
  pageSize = 10,
}: DataTableProps<TData>) {
  const [sorting, setSorting] = useState<SortingState>([])
  const [globalFilter, setGlobalFilter] = useState('')
  const [density, setDensity] = useState<'compact' | 'comfortable'>('comfortable')

  const table = useReactTable({
    data: data ?? [],
    columns,
    state: { sorting, globalFilter },
    onSortingChange: setSorting,
    onGlobalFilterChange: setGlobalFilter,
    getCoreRowModel: getCoreRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    getRowId: getRowId as any,
    initialState: {
      pagination: {
        pageSize,
      },
    },
  })

  if (loading) {
    return (
      <div className="space-y-2">
        {Array.from({ length: 5 }).map((_, i) => (
          <Skeleton key={i} className="h-9 w-full" />
        ))}
      </div>
    )
  }

  if (!data || data.length === 0) {
    return <EmptyState title={emptyTitle} description={emptyDescription} />
  }

  return (
    <div className="space-y-3">
      {(searchable || data.length > pageSize) && (
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-border/70 bg-muted/25 p-2">
          {searchable ? (
            <div className="relative w-full sm:max-w-sm">
              <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                value={globalFilter}
                onChange={(event) => setGlobalFilter(event.target.value)}
                placeholder={searchPlaceholder}
                className="h-10 rounded-xl border-border/70 bg-card pl-9 shadow-sm"
              />
            </div>
          ) : (
            <span />
          )}
          <div className="flex items-center gap-1 rounded-xl border border-border/70 bg-card p-1 shadow-sm">
            <Button
              type="button"
              variant={density === 'compact' ? 'secondary' : 'ghost'}
              size="icon-xs"
              title="Densidade compacta"
              onClick={() => setDensity('compact')}
            >
              <Rows3 className="size-3.5" />
            </Button>
            <Button
              type="button"
              variant={density === 'comfortable' ? 'secondary' : 'ghost'}
              size="icon-xs"
              title="Densidade confortável"
              onClick={() => setDensity('comfortable')}
            >
              <StretchHorizontal className="size-3.5" />
            </Button>
          </div>
        </div>
      )}

      <div className="overflow-hidden rounded-2xl border border-border/70 bg-card shadow-sm shadow-slate-950/[0.035]">
        <Table>
          <TableHeader className="max-sm:hidden">
            {table.getHeaderGroups().map((headerGroup) => (
              <TableRow key={headerGroup.id} className="border-border/70 bg-muted/45 hover:bg-muted/45">
                {headerGroup.headers.map((header) => {
                  const canSort = header.column.getCanSort()
                  const sortDir = header.column.getIsSorted()
                  return (
                    <TableHead
                      key={header.id}
                      className={cn(
                        'sticky top-0 z-[1] h-11 bg-muted/88 text-[11px] font-semibold uppercase tracking-[0.08em] text-muted-foreground backdrop-blur',
                        canSort && 'cursor-pointer select-none',
                      )}
                      onClick={header.column.getToggleSortingHandler()}
                    >
                      {header.isPlaceholder ? null : (
                        <span className="inline-flex items-center gap-1">
                          {flexRender(header.column.columnDef.header, header.getContext())}
                          {canSort ? (
                            sortDir === 'asc' ? (
                              <ArrowUp className="size-3" />
                            ) : sortDir === 'desc' ? (
                              <ArrowDown className="size-3" />
                            ) : (
                              <ArrowUpDown className="size-3 text-muted-foreground/50" />
                            )
                          ) : null}
                        </span>
                      )}
                    </TableHead>
                  )
                })}
              </TableRow>
            ))}
          </TableHeader>
          <TableBody className="max-sm:block max-sm:space-y-3 max-sm:bg-muted/20 max-sm:p-2">
            {table.getRowModel().rows.length > 0 ? (
              table.getRowModel().rows.map((row) => (
                <TableRow
                  key={row.id}
                  onClick={onRowClick ? () => onRowClick(row.original) : undefined}
                  className={cn(
                    'group border-border/55 transition hover:bg-muted/35 max-sm:block max-sm:rounded-2xl max-sm:border max-sm:bg-card max-sm:shadow-sm',
                    onRowClick && 'cursor-pointer',
                  )}
                >
                  {row.getVisibleCells().map((cell) => (
                    <TableCell
                      key={cell.id}
                      className={cn(
                        'text-[13px] max-sm:flex max-sm:items-start max-sm:justify-between max-sm:gap-4 max-sm:border-b max-sm:border-border/50 max-sm:last:border-0',
                        density === 'compact' ? 'px-3 py-2' : 'px-3 py-3',
                      )}
                    >
                      <span className="hidden text-[11px] font-semibold uppercase tracking-[0.08em] text-muted-foreground max-sm:block">
                        {typeof cell.column.columnDef.header === 'string'
                          ? cell.column.columnDef.header
                          : ''}
                      </span>
                      <span className="min-w-0 max-sm:text-right">
                        {flexRender(cell.column.columnDef.cell, cell.getContext())}
                      </span>
                    </TableCell>
                  ))}
                </TableRow>
              ))
            ) : (
              <TableRow>
                <TableCell colSpan={columns.length} className="h-24 text-center text-sm text-muted-foreground">
                  Nenhum registro corresponde à busca.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>

      {table.getPageCount() > 1 ? (
        <div className="flex flex-wrap items-center justify-between gap-2 rounded-2xl border border-border/70 bg-card/75 px-3 py-2 text-xs text-muted-foreground shadow-sm shadow-slate-950/[0.025]">
          <span>
            Página {table.getState().pagination.pageIndex + 1} de {table.getPageCount()} ·{' '}
            {table.getFilteredRowModel().rows.length} registro(s)
          </span>
          <div className="flex items-center gap-2">
            <Button
              type="button"
              variant="outline"
              size="xs"
              disabled={!table.getCanPreviousPage()}
              onClick={() => table.previousPage()}
            >
              Anterior
            </Button>
            <Button
              type="button"
              variant="outline"
              size="xs"
              disabled={!table.getCanNextPage()}
              onClick={() => table.nextPage()}
            >
              Próxima
            </Button>
          </div>
        </div>
      ) : null}
    </div>
  )
}
