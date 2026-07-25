import { useState } from 'react'
import type { ColumnDef } from '@tanstack/react-table'
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { Loader2, Package, Search, Users } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { DataTable } from '@/components/shared/DataTable'
import { EmptyState } from '@/components/shared/EmptyState'
import { PageHeader } from '@/components/shared/PageHeader'
import { SectionCard } from '@/components/shared/SectionCard'
import { SegmentBadge } from '@/components/shared/SegmentBadge'
import { RelativeTime } from '@/components/shared/RelativeTime'
import { RecommendationResultsTable } from '@/components/shared/RecommendationResultsTable'
import { useCustomer, useCustomers, useRfmSummary } from '@/hooks/use-dashboard'
import { useRecommendByCustomer } from '@/hooks/use-actions'
import { formatCurrency, formatNumber } from '@/lib/format'
import { SEGMENT_LABELS, getSegmentColor, getSegmentLabel } from '@/lib/segments'
import type { CustomerSummary } from '@/types/api'

export function CustomersPage() {
  const [segment, setSegment] = useState<string>('all')
  const [selectedCustomerId, setSelectedCustomerId] = useState<string | null>(null)

  const rfmSummary = useRfmSummary()
  const customers = useCustomers(segment === 'all' ? undefined : segment, 100, 0)

  const chartData = (rfmSummary.data ?? []).map((row) => ({
    segmentKey: row.segment,
    segment: getSegmentLabel(row.segment),
    customer_count: row.customer_count,
    color: getSegmentColor(row.segment)?.chart ?? '#64748b',
  }))

  const columns: ColumnDef<CustomerSummary, any>[] = [
    { accessorKey: 'name', header: 'Cliente' },
    {
      accessorKey: 'rfm_segment',
      header: 'Segmento',
      cell: ({ getValue }) => <SegmentBadge segment={getValue<string>()} />,
    },
    { accessorKey: 'rfm_score', header: 'Score RFM' },
    {
      accessorKey: 'rfm_monetary',
      header: 'Valor total',
      cell: ({ getValue }) => formatCurrency(getValue<number>()),
    },
    {
      id: 'location',
      header: 'Local',
      accessorFn: (row) => [row.city_name, row.state_initials].filter(Boolean).join('/'),
      cell: ({ getValue }) => {
        const value = getValue<string>()
        return value ? value : <span className="text-muted-foreground">—</span>
      },
    },
    {
      accessorKey: 'last_order_at',
      header: 'Última compra',
      cell: ({ getValue }) => <RelativeTime value={getValue<string>()} />,
    },
  ]

  return (
    <div className="space-y-6">
      <PageHeader
        title="Clientes"
        description="Analise segmentação RFM, concentração de clientes e oportunidades individuais."
        icon={Users}
      />

      <div className="grid gap-4 lg:grid-cols-3">
        <SectionCard
          title="Distribuição por segmento RFM"
          description="As cores do gráfico seguem os mesmos labels usados na lista de clientes."
          icon={Users}
          className="lg:col-span-2"
        >
            {rfmSummary.isLoading ? (
              <div className="h-56 animate-pulse rounded-md bg-muted" />
            ) : chartData.length === 0 ? (
              <EmptyState
                title="RFM ainda não calculado"
                description='Rode "Rodar algoritmos" na Home para segmentar os clientes.'
              />
            ) : (
              <ResponsiveContainer width="100%" height={230}>
                <BarChart data={chartData} margin={{ top: 8, right: 8, bottom: 4, left: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} />
                  <XAxis
                    dataKey="segment"
                    interval={0}
                    fontSize={12}
                    tick={(props) => <SegmentAxisTick {...props} data={chartData} />}
                  />
                  <YAxis allowDecimals={false} fontSize={12} />
                  <Tooltip formatter={(value) => [formatNumber(Number(value)), 'Clientes']} />
                  <Bar dataKey="customer_count" radius={[5, 5, 0, 0]}>
                    {chartData.map((entry) => (
                      <Cell key={entry.segmentKey} fill={entry.color} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            )}
        </SectionCard>
        <SectionCard
          title="Resumo por segmento"
          description="Clique em um segmento para filtrar a lista."
          contentClassName="space-y-2"
        >
            {(rfmSummary.data ?? []).map((row) => (
              <button
                key={row.segment}
                type="button"
                onClick={() => setSegment(row.segment)}
                className="flex w-full items-center justify-between rounded-lg border bg-card px-3 py-2 text-left text-sm transition hover:bg-muted"
              >
                <div className="flex items-center gap-2">
                  <span
                    className="size-2.5 rounded-full"
                    style={{ backgroundColor: getSegmentColor(row.segment)?.chart ?? '#64748b' }}
                  />
                  <SegmentBadge segment={row.segment} />
                </div>
                <span className="font-medium">{formatNumber(row.customer_count)}</span>
              </button>
            ))}
            {!rfmSummary.isLoading && (rfmSummary.data ?? []).length === 0 && (
              <p className="text-sm text-muted-foreground">Sem dados ainda.</p>
            )}
        </SectionCard>
      </div>

      <SectionCard
        title="Lista de clientes"
        description="Abra um cliente para ver detalhes, histórico e recomendações."
        actions={
          <Select value={segment} onValueChange={setSegment}>
            <SelectTrigger className="w-48">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Todos os segmentos</SelectItem>
              {Object.entries(SEGMENT_LABELS).map(([value, label]) => (
                <SelectItem key={value} value={value}>
                  {label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        }
      >
          <DataTable
            columns={columns}
            data={customers.data}
            loading={customers.isLoading}
            emptyTitle="Nenhum cliente com RFM calculado"
            emptyDescription='Rode "Rodar algoritmos" na Home para segmentar os clientes.'
            getRowId={(row) => row.customer_id}
            onRowClick={(row) => setSelectedCustomerId(row.customer_id)}
            searchable
            searchPlaceholder="Buscar cliente, cidade ou segmento..."
          />
      </SectionCard>

      <CustomerDetailSheet
        customerId={selectedCustomerId}
        onOpenChange={(open) => !open && setSelectedCustomerId(null)}
      />
    </div>
  )
}

function SegmentAxisTick({
  x,
  y,
  payload,
  data,
}: {
  x?: string | number
  y?: string | number
  payload?: { value: string }
  data: { segment: string; color: string }[]
}) {
  const item = data.find((entry) => entry.segment === payload?.value)
  return (
    <text
      x={x}
      y={y}
      dy={14}
      textAnchor="middle"
      fill={item?.color ?? 'currentColor'}
      className="text-[11px] font-medium"
    >
      {payload?.value}
    </text>
  )
}

function CustomerDetailSheet({
  customerId,
  onOpenChange,
}: {
  customerId: string | null
  onOpenChange: (open: boolean) => void
}) {
  const customer = useCustomer(customerId ?? undefined)
  const recommend = useRecommendByCustomer()

  return (
    <Sheet open={Boolean(customerId)} onOpenChange={onOpenChange}>
      <SheetContent className="w-full gap-0 overflow-y-auto sm:max-w-lg">
        <SheetHeader>
          <SheetTitle>{customer.data?.name ?? 'Detalhe do cliente'}</SheetTitle>
          <SheetDescription>
            {customer.data?.email ?? customer.data?.document ?? ''}
          </SheetDescription>
        </SheetHeader>

        <div className="space-y-6 px-4 pb-6">
          {customer.isLoading ? (
            <div className="h-40 animate-pulse rounded-md bg-muted" />
          ) : customer.data ? (
            <>
              <div className="grid grid-cols-2 gap-3">
                <div className="rounded-lg border bg-card p-3 shadow-sm">
                  <p className="text-xs text-muted-foreground">Segmento</p>
                  <SegmentBadge segment={customer.data.rfm_segment} />
                </div>
                <div className="rounded-lg border bg-card p-3 shadow-sm">
                  <p className="text-xs text-muted-foreground">Score RFM</p>
                  <p className="text-sm font-medium">{customer.data.rfm_score ?? '—'}</p>
                </div>
                <div className="rounded-lg border bg-card p-3 shadow-sm">
                  <p className="text-xs text-muted-foreground">Valor total</p>
                  <p className="text-sm font-medium">{formatCurrency(customer.data.rfm_monetary)}</p>
                </div>
                <div className="rounded-lg border bg-card p-3 shadow-sm">
                  <p className="text-xs text-muted-foreground">Última compra</p>
                  <p className="text-sm font-medium">
                    <RelativeTime value={customer.data.last_order_at} />
                  </p>
                </div>
                <div className="rounded-lg border bg-card p-3 shadow-sm">
                  <p className="text-xs text-muted-foreground">Localização</p>
                  <p className="text-sm font-medium">
                    {[customer.data.city_name, customer.data.state_initials]
                      .filter(Boolean)
                      .join('/') || '—'}
                  </p>
                </div>
              </div>

              <div>
                <h3 className="mb-2 flex items-center gap-1.5 text-sm font-medium">
                  <Package className="size-4" /> Produtos comprados
                </h3>
                {customer.data.products_purchased.length === 0 ? (
                  <p className="text-sm text-muted-foreground">Nenhum produto encontrado.</p>
                ) : (
                  <ul className="space-y-1 text-sm">
                    {customer.data.products_purchased.map((product) => (
                      <li key={product.product_id} className="flex justify-between border-b py-1.5">
                        <span>{product.name}</span>
                        <span className="text-muted-foreground">{product.code}</span>
                      </li>
                    ))}
                  </ul>
                )}
              </div>

              <div>
                <div className="mb-2 flex items-center justify-between">
                  <h3 className="text-sm font-medium">Recomendações para este cliente</h3>
                  <Button
                    size="sm"
                    disabled={recommend.isPending}
                    onClick={() =>
                      customerId && recommend.mutate({ customerId, limit: 10 })
                    }
                  >
                    {recommend.isPending ? (
                      <Loader2 className="size-4 animate-spin" />
                    ) : (
                      <Search className="size-4" />
                    )}
                    Gerar
                  </Button>
                </div>
                {recommend.data ? (
                  <RecommendationResultsTable results={recommend.data} loading={recommend.isPending} />
                ) : (
                  <p className="text-sm text-muted-foreground">
                    Clique em "Gerar" para ver recomendações.
                  </p>
                )}
              </div>
            </>
          ) : (
            <p className="text-sm text-muted-foreground">Cliente não encontrado.</p>
          )}
        </div>
      </SheetContent>
    </Sheet>
  )
}
