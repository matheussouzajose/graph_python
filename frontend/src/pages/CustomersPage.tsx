import { useState } from 'react'
import type { ReactNode } from 'react'
import type { ColumnDef } from '@tanstack/react-table'
import { useNavigate } from 'react-router-dom'
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { Bot, HeartPulse, Loader2, MapPin, Package, Search, Sparkles, Users } from 'lucide-react'
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
      <section className="dark-panel relative overflow-hidden rounded-3xl p-5 sm:p-6">
        <div className="surface-glow absolute right-8 top-4 h-44 w-44 rounded-full bg-violet-400/18 blur-3xl" />
        <div className="absolute -bottom-20 left-1/4 h-44 w-44 rounded-full bg-teal-300/12 blur-3xl" />
        <div className="relative grid gap-5 lg:grid-cols-[1fr_360px] lg:items-center">
          <div>
            <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/8 px-3 py-1.5 text-xs text-violet-100">
              <HeartPulse className="size-3.5" />
              CRM inteligente
            </div>
            <h2 className="mt-4 max-w-2xl text-3xl font-semibold tracking-normal">
              Priorize quem compra, quem esfriou e quem merece próxima ação.
            </h2>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-white/55">
              Segmentos RFM deixam de ser relatório e viram fila de decisão para retenção,
              reativação e expansão.
            </p>
          </div>
          <div className="grid gap-3">
            <CustomerSignal label="Segmentos ativos" value={formatNumber(chartData.length)} />
            <CustomerSignal label="Clientes listados" value={formatNumber(customers.data?.length ?? 0)} />
            <CustomerSignal label="Filtro atual" value={segment === 'all' ? 'Todos' : getSegmentLabel(segment)} />
          </div>
        </div>
      </section>

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

function CustomerSignal({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-white/10 bg-white/[0.075] p-3">
      <div className="flex items-center justify-between gap-3">
        <p className="text-xs text-white/45">{label}</p>
        <Sparkles className="size-4 text-violet-200" />
      </div>
      <p className="mt-1 truncate text-lg font-semibold">{value}</p>
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
  const navigate = useNavigate()
  const customer = useCustomer(customerId ?? undefined)
  const recommend = useRecommendByCustomer()

  function askAboutCustomer() {
    const name = customer.data?.name ?? customer.data?.document ?? 'este cliente'
    navigate('/oraculo', {
      state: {
        question: `Analise o cliente ${name}: segmento RFM, risco, histórico e próximas ações comerciais.`,
      },
    })
  }

  return (
    <Sheet open={Boolean(customerId)} onOpenChange={onOpenChange}>
      <SheetContent className="w-full gap-0 overflow-y-auto sm:max-w-xl">
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
              <div className="dark-panel relative overflow-hidden rounded-3xl p-4">
                <div className="surface-glow absolute right-0 top-0 h-28 w-28 rounded-full bg-violet-400/20 blur-2xl" />
                <div className="relative grid grid-cols-2 gap-3">
                  <CustomerMetric label="Segmento" value={<SegmentBadge segment={customer.data.rfm_segment} />} />
                  <CustomerMetric label="Score RFM" value={customer.data.rfm_score ?? '—'} />
                  <CustomerMetric label="Valor total" value={formatCurrency(customer.data.rfm_monetary)} />
                  <CustomerMetric
                    label="Última compra"
                    value={<RelativeTime value={customer.data.last_order_at} />}
                  />
                </div>
              </div>

              <div className="grid gap-3 sm:grid-cols-2">
                <CustomerInfoTile
                  icon={MapPin}
                  label="Localização"
                  value={
                    [customer.data.city_name, customer.data.state_initials]
                      .filter(Boolean)
                      .join('/') || '—'
                  }
                />
                <CustomerInfoTile
                  icon={Users}
                  label="Contato"
                  value={customer.data.email ?? customer.data.document ?? '—'}
                />
              </div>

              <Button className="w-full rounded-2xl" onClick={askAboutCustomer}>
                <Bot className="size-4" />
                Perguntar ao Oráculo sobre este cliente
              </Button>

              <div className="rounded-2xl border bg-card p-4 shadow-sm">
                <h3 className="mb-2 flex items-center gap-1.5 text-sm font-medium">
                  <Package className="size-4" /> Produtos comprados
                </h3>
                {customer.data.products_purchased.length === 0 ? (
                  <p className="text-sm text-muted-foreground">Nenhum produto encontrado.</p>
                ) : (
                  <ul className="space-y-2 text-sm">
                    {customer.data.products_purchased.map((product) => (
                      <li key={product.product_id} className="flex justify-between gap-3 rounded-xl border bg-muted/25 px-3 py-2">
                        <span className="min-w-0 truncate">{product.name}</span>
                        <span className="text-muted-foreground">{product.code}</span>
                      </li>
                    ))}
                  </ul>
                )}
              </div>

              <div className="rounded-2xl border bg-card p-4 shadow-sm">
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

function CustomerMetric({
  label,
  value,
}: {
  label: string
  value: ReactNode
}) {
  return (
    <div className="rounded-2xl border border-white/10 bg-white/[0.075] p-3">
      <p className="text-xs text-white/45">{label}</p>
      <div className="mt-1 truncate text-sm font-semibold">{value}</div>
    </div>
  )
}

function CustomerInfoTile({
  icon: Icon,
  label,
  value,
}: {
  icon: typeof Users
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
