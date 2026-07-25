import { useMemo, useState } from 'react'
import type { ColumnDef } from '@tanstack/react-table'
import { Filter, ReceiptText, RotateCcw, X } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { DataTable } from '@/components/shared/DataTable'
import { EmptyState } from '@/components/shared/EmptyState'
import { PageHeader } from '@/components/shared/PageHeader'
import { RelativeTime } from '@/components/shared/RelativeTime'
import { SectionCard } from '@/components/shared/SectionCard'
import { useOrderFilters, useOrders } from '@/hooks/use-orders'
import { formatCurrency, formatNumber } from '@/lib/format'
import type { Order, OrderFilterFacet, OrderFilterParams, OrderFilterOption } from '@/types/api'

const PAGE_SIZE = 50

const STATUS_LABELS: Record<string, string> = {
  paid: 'Pago',
  pending: 'Pendente',
  canceled: 'Cancelado',
  cancelled: 'Cancelado',
  shipped: 'Enviado',
  delivered: 'Entregue',
}

function labelStatus(value: string | null) {
  if (!value) return '—'
  return STATUS_LABELS[value] ?? value
}

function textValue(value: unknown) {
  return typeof value === 'string' && value.trim() ? value : '—'
}

function moneyFromSummary(summary: Record<string, unknown>) {
  const value = summary.total_value
  if (typeof value === 'number') return value
  if (typeof value === 'string') return Number(value)
  return undefined
}

function getCity(order: Order) {
  const city = order.address?.city
  if (city && typeof city === 'object' && 'name' in city) {
    return textValue(city.name)
  }
  return '—'
}

function getState(order: Order) {
  const state = order.address?.state
  if (state && typeof state === 'object' && 'initials' in state) {
    return textValue(state.initials)
  }
  return '—'
}

function getCustomerName(order: Order) {
  return textValue(order.customer?.name)
}

function getProductNames(order: Order) {
  return order.products
    .map((product) => product.name)
    .filter((name): name is string => typeof name === 'string' && name.trim().length > 0)
    .slice(0, 3)
    .join(', ')
}

export function OrdersPage() {
  const [filters, setFilters] = useState<OrderFilterParams>({})
  const [offset, setOffset] = useState(0)
  const orders = useOrders(filters, PAGE_SIZE, offset)
  const facets = useOrderFilters(filters)
  const selectedCount = Object.values(filters).reduce((total, values) => total + values.length, 0)

  const columns = useMemo<ColumnDef<Order, any>[]>(
    () => [
      {
        accessorKey: 'code',
        header: 'Pedido',
        cell: ({ row }) => (
          <span className="font-medium">#{row.original.code ?? row.original.external_order_id}</span>
        ),
      },
      {
        id: 'customer',
        header: 'Cliente',
        accessorFn: getCustomerName,
      },
      {
        accessorKey: 'status',
        header: 'Status',
        cell: ({ getValue }) => <Badge variant="outline">{labelStatus(getValue<string | null>())}</Badge>,
      },
      {
        id: 'location',
        header: 'Local',
        accessorFn: (order) => `${getCity(order)}/${getState(order)}`,
      },
      {
        id: 'products',
        header: 'Produtos',
        accessorFn: getProductNames,
        cell: ({ getValue }) => getValue<string>() || <span className="text-muted-foreground">—</span>,
      },
      {
        id: 'total',
        header: 'Total',
        accessorFn: (order) => moneyFromSummary(order.summary),
        cell: ({ getValue }) => formatCurrency(getValue<number | undefined>()),
      },
      {
        accessorKey: 'external_created_at',
        header: 'Criado',
        cell: ({ getValue }) => <RelativeTime value={getValue<string | null>()} />,
      },
    ],
    [],
  )

  function updateFilter(key: string, value: string, checked: boolean) {
    setOffset(0)
    setFilters((current) => {
      const values = new Set(current[key] ?? [])
      if (checked) values.add(value)
      else values.delete(value)
      const next = { ...current, [key]: Array.from(values) }
      if (next[key].length === 0) delete next[key]
      return next
    })
  }

  function clearFilter(key: string, value?: string) {
    setOffset(0)
    setFilters((current) => {
      const next = { ...current }
      if (!value) {
        delete next[key]
        return next
      }
      const values = (next[key] ?? []).filter((item) => item !== value)
      if (values.length > 0) next[key] = values
      else delete next[key]
      return next
    })
  }

  const total = orders.data?.total ?? 0
  const pageStart = total === 0 ? 0 : offset + 1
  const pageEnd = Math.min(offset + PAGE_SIZE, total)

  return (
    <div className="space-y-6">
      <PageHeader
        title="Pedidos"
        description="Explore pedidos por filtros encadeados de integração, status, origem, localização e produto."
        icon={ReceiptText}
      />

      <SectionCard
        title="Filtros de pedidos"
        description="As opções são recalculadas conforme os filtros selecionados."
        icon={Filter}
        actions={
          selectedCount > 0 ? (
            <Button variant="outline" size="sm" onClick={() => { setFilters({}); setOffset(0) }}>
              <RotateCcw className="size-4" />
              Limpar filtros
            </Button>
          ) : null
        }
      >
        <div className="space-y-4">
          <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
            {(facets.data?.facets ?? []).map((facet) => (
              <FacetPicker
                key={facet.key}
                facet={facet}
                selected={filters[facet.key] ?? []}
                onToggle={(value, checked) => updateFilter(facet.key, value, checked)}
              />
            ))}
          </div>

          {selectedCount > 0 ? (
            <div className="flex flex-wrap gap-1.5">
              {Object.entries(filters).flatMap(([key, values]) =>
                values.map((value) => (
                  <button
                    key={`${key}-${value}`}
                    type="button"
                    onClick={() => clearFilter(key, value)}
                    className="inline-flex items-center gap-1 rounded-lg border bg-card px-2 py-1 text-xs"
                  >
                    {findSelectedLabel(facets.data?.facets, key, value)}
                    <X className="size-3" />
                  </button>
                )),
              )}
            </div>
          ) : null}
        </div>
      </SectionCard>

      <SectionCard
        title="Pedidos encontrados"
        description={
          total > 0
            ? `${formatNumber(pageStart)}-${formatNumber(pageEnd)} de ${formatNumber(total)} pedido(s)`
            : 'Nenhum pedido para os filtros atuais.'
        }
      >
        {orders.data?.items.length === 0 && !orders.isLoading ? (
          <EmptyState
            title="Nenhum pedido encontrado"
            description="Remova algum filtro ou sincronize uma integração para ampliar a base."
          />
        ) : (
          <div className="space-y-3">
            <DataTable
              columns={columns}
              data={orders.data?.items}
              loading={orders.isLoading}
              emptyTitle="Nenhum pedido encontrado"
              getRowId={(row) => row.id}
              searchable
              searchPlaceholder="Buscar nesta página..."
              pageSize={PAGE_SIZE}
            />
            <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-muted-foreground">
              <span>
                {formatNumber(pageStart)}-{formatNumber(pageEnd)} de {formatNumber(total)}
              </span>
              <div className="flex items-center gap-2">
                <Button
                  type="button"
                  variant="outline"
                  size="xs"
                  disabled={offset === 0 || orders.isFetching}
                  onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
                >
                  Anterior
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  size="xs"
                  disabled={offset + PAGE_SIZE >= total || orders.isFetching}
                  onClick={() => setOffset(offset + PAGE_SIZE)}
                >
                  Próxima
                </Button>
              </div>
            </div>
          </div>
        )}
      </SectionCard>
    </div>
  )
}

function FacetPicker({
  facet,
  selected,
  onToggle,
}: {
  facet: OrderFilterFacet
  selected: string[]
  onToggle: (value: string, checked: boolean) => void
}) {
  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button variant="outline" className="justify-between">
          <span className="truncate">{facet.label}</span>
          {selected.length > 0 ? <Badge variant="secondary">{selected.length}</Badge> : null}
        </Button>
      </PopoverTrigger>
      <PopoverContent align="start" className="w-80">
        <div className="space-y-2">
          <div>
            <p className="text-sm font-medium">{facet.label}</p>
            <p className="text-xs text-muted-foreground">Selecione uma ou mais opções.</p>
          </div>
          <div className="max-h-72 space-y-1 overflow-y-auto pr-1">
            {facet.options.length === 0 ? (
              <p className="py-3 text-sm text-muted-foreground">Sem opções disponíveis.</p>
            ) : (
              facet.options.map((option) => (
                <FacetOption
                  key={option.value}
                  option={option}
                  checked={selected.includes(option.value)}
                  onCheckedChange={(checked) => onToggle(option.value, checked)}
                />
              ))
            )}
          </div>
        </div>
      </PopoverContent>
    </Popover>
  )
}

function FacetOption({
  option,
  checked,
  onCheckedChange,
}: {
  option: OrderFilterOption
  checked: boolean
  onCheckedChange: (checked: boolean) => void
}) {
  return (
    <label className="flex cursor-pointer items-center gap-2 rounded-md px-2 py-1.5 text-sm hover:bg-muted">
      <input
        type="checkbox"
        checked={checked}
        onChange={(event) => onCheckedChange(event.target.checked)}
        className="size-4 accent-primary"
      />
      <span className="min-w-0 flex-1 truncate">{option.label}</span>
      <span className="text-xs text-muted-foreground">{formatNumber(option.count)}</span>
    </label>
  )
}

function findSelectedLabel(facets: OrderFilterFacet[] | undefined, key: string, value: string) {
  const option = facets
    ?.find((facet) => facet.key === key)
    ?.options.find((item) => item.value === value)
  return option?.label ?? value
}
