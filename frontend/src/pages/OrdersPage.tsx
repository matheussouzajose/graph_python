import { useMemo, useState } from 'react'
import type { ColumnDef } from '@tanstack/react-table'
import { Activity, Filter, MapPin, Package, SlidersHorizontal, User } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet'
import { DataTable } from '@/components/shared/DataTable'
import { EmptyState } from '@/components/shared/EmptyState'
import { FilterBar, type FilterChip } from '@/components/shared/FilterBar'
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
  const [selectedOrder, setSelectedOrder] = useState<Order | null>(null)
  const orders = useOrders(filters, PAGE_SIZE, offset)
  const facets = useOrderFilters(filters)
  const selectedCount = Object.values(filters).reduce((total, values) => total + values.length, 0)
  const selectedChips = useMemo<FilterChip[]>(
    () =>
      Object.entries(filters).flatMap(([key, values]) =>
        values.map((value) => ({
          key,
          value,
          label: findSelectedLabel(facets.data?.facets, key, value),
        })),
      ),
    [facets.data?.facets, filters],
  )

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
      <section className="dark-panel relative overflow-hidden rounded-3xl p-5 sm:p-6">
        <div className="surface-glow absolute right-0 top-0 h-40 w-40 rounded-full bg-blue-400/18 blur-3xl" />
        <div className="relative grid gap-5 lg:grid-cols-[1fr_auto] lg:items-center">
          <div>
            <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/8 px-3 py-1.5 text-xs text-blue-100">
              <SlidersHorizontal className="size-3.5" />
              Investigação comercial
            </div>
            <h2 className="mt-4 max-w-2xl text-3xl font-semibold tracking-normal">
              Encontre padrões de compra antes de abrir a planilha.
            </h2>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-white/55">
              Combine filtros, navegue por lotes e leia pedidos como sinais de comportamento,
              região, produto e receita.
            </p>
          </div>
          <div className="grid min-w-72 gap-3 sm:grid-cols-3 lg:grid-cols-1">
            <OrderSignal label="Encontrados" value={formatNumber(total)} />
            <OrderSignal label="Nesta página" value={`${formatNumber(pageStart)}-${formatNumber(pageEnd)}`} />
            <OrderSignal label="Filtros ativos" value={formatNumber(selectedCount)} />
          </div>
        </div>
      </section>

      <SectionCard
        title="Filtros de pedidos"
        description="As opções são recalculadas conforme os filtros selecionados."
        icon={Filter}
      >
        <FilterBar
          title="Filtro inteligente"
          description="Combine facetas e mantenha os filtros ativos sempre visíveis."
          selected={selectedChips}
          onRemove={(chip) => clearFilter(chip.key, chip.value)}
          onClear={() => {
            setFilters({})
            setOffset(0)
          }}
        >
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
        </FilterBar>
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
              onRowClick={setSelectedOrder}
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

      <OrderDetailSheet order={selectedOrder} onClose={() => setSelectedOrder(null)} />
    </div>
  )
}

function OrderSignal({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-white/10 bg-white/[0.075] p-3">
      <div className="flex items-center justify-between gap-3">
        <p className="text-xs text-white/45">{label}</p>
        <Activity className="size-4 text-blue-200" />
      </div>
      <p className="mt-1 truncate text-lg font-semibold">{value}</p>
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

function OrderDetailSheet({ order, onClose }: { order: Order | null; onClose: () => void }) {
  const products = order?.products ?? []

  return (
    <Sheet open={Boolean(order)} onOpenChange={(open) => !open && onClose()}>
      <SheetContent className="w-full gap-0 overflow-y-auto sm:max-w-xl">
        <SheetHeader>
          <SheetTitle>Pedido #{order?.code ?? order?.external_order_id ?? '—'}</SheetTitle>
          <SheetDescription>
            {order?.external_created_at ? <RelativeTime value={order.external_created_at} /> : 'Sem data ERP'}
          </SheetDescription>
        </SheetHeader>

        {order ? (
          <div className="space-y-5 px-4 pb-6">
            <div className="dark-panel relative overflow-hidden rounded-3xl p-4">
              <div className="surface-glow absolute right-0 top-0 h-28 w-28 rounded-full bg-blue-400/20 blur-2xl" />
              <div className="relative grid gap-3 sm:grid-cols-3">
                <DetailMetric label="Status" value={labelStatus(order.status)} />
                <DetailMetric label="Total" value={formatCurrency(moneyFromSummary(order.summary))} />
                <DetailMetric label="Origem" value={textValue(order.origin)} />
              </div>
            </div>

            <div className="grid gap-3 sm:grid-cols-2">
              <DetailTile icon={User} label="Cliente" value={getCustomerName(order)} />
              <DetailTile icon={MapPin} label="Localização" value={`${getCity(order)}/${getState(order)}`} />
            </div>

            <div className="rounded-2xl border bg-card p-4 shadow-sm">
              <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold">
                <Package className="size-4 text-primary" />
                Produtos do pedido
              </h3>
              {products.length === 0 ? (
                <p className="text-sm text-muted-foreground">Nenhum produto encontrado.</p>
              ) : (
                <ul className="space-y-2">
                  {products.map((product, index) => (
                    <li
                      key={`${String(product.id ?? product.code ?? index)}`}
                      className="rounded-xl border bg-muted/25 px-3 py-2"
                    >
                      <p className="truncate text-sm font-medium">{textValue(product.name)}</p>
                      <p className="mt-0.5 text-xs text-muted-foreground">
                        Código {textValue(product.code)}
                      </p>
                    </li>
                  ))}
                </ul>
              )}
            </div>

            <div className="rounded-2xl border bg-card p-4 shadow-sm">
              <h3 className="mb-3 text-sm font-semibold">Dados operacionais</h3>
              <div className="grid gap-2 text-sm">
                <KeyValue label="ID externo" value={order.external_order_id} />
                <KeyValue label="Integração" value={order.integration_id} />
                <KeyValue label="Atualizado no ERP" value={order.external_updated_at ?? '—'} />
                <KeyValue label="Observações" value={textValue(order.observations)} />
              </div>
            </div>
          </div>
        ) : null}
      </SheetContent>
    </Sheet>
  )
}

function DetailMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-white/10 bg-white/[0.075] p-3">
      <p className="text-xs text-white/45">{label}</p>
      <p className="mt-1 truncate text-sm font-semibold">{value}</p>
    </div>
  )
}

function DetailTile({
  icon: Icon,
  label,
  value,
}: {
  icon: typeof User
  label: string
  value: string
}) {
  return (
    <div className="rounded-2xl border bg-card p-4 shadow-sm">
      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        <Icon className="size-4 text-primary" />
        {label}
      </div>
      <p className="mt-2 truncate text-sm font-semibold">{value}</p>
    </div>
  )
}

function KeyValue({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between gap-3 border-b border-border/60 py-2 last:border-0">
      <span className="text-muted-foreground">{label}</span>
      <span className="min-w-0 truncate text-right font-medium">{value}</span>
    </div>
  )
}
