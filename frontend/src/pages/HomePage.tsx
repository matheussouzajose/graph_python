import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import {
  Database,
  Gauge,
  GitBranch,
  Loader2,
  Package,
  Play,
  RefreshCw,
  ReceiptText,
  Sparkles,
  TrendingUp,
  Users,
  Wallet,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { StatCard } from '@/components/shared/StatCard'
import { RelativeTime } from '@/components/shared/RelativeTime'
import { EmptyState } from '@/components/shared/EmptyState'
import { SectionCard } from '@/components/shared/SectionCard'
import {
  useGraphSyncAction,
  useRunAlgorithmsAction,
  useRunEmbeddingsAction,
  useSyncIntegrationAction,
} from '@/hooks/use-actions'
import { useOverview, useSyncStatus } from '@/hooks/use-dashboard'
import { formatCurrency, formatNumber } from '@/lib/format'

const STATUS_LABELS: Record<string, string> = {
  paid: 'Pago',
  pending: 'Pendente',
  canceled: 'Cancelado',
  cancelled: 'Cancelado',
  shipped: 'Enviado',
  delivered: 'Entregue',
}

const STATUS_COLORS: Record<string, string> = {
  paid: '#059669',
  delivered: '#2563eb',
  shipped: '#0891b2',
  pending: '#d97706',
  canceled: '#dc2626',
  cancelled: '#dc2626',
}

export function HomePage() {
  const overview = useOverview()
  const syncStatus = useSyncStatus()
  const syncIntegration = useSyncIntegrationAction()
  const graphSync = useGraphSyncAction()
  const algorithms = useRunAlgorithmsAction()
  const embeddings = useRunEmbeddingsAction()
  const firstActiveIntegration = syncStatus.data?.integrations.find((integration) => integration.is_active)

  const statusData = (overview.data?.orders_by_status ?? []).map((item) => ({
    key: item.status,
    status: STATUS_LABELS[item.status] ?? item.status,
    count: item.count,
    color: STATUS_COLORS[item.status] ?? '#64748b',
  }))

  return (
    <div className="space-y-6">
      <section className="dark-panel relative overflow-hidden rounded-3xl p-5 sm:p-6">
        <div className="surface-glow absolute right-4 top-4 h-44 w-44 rounded-full bg-teal-400/18 blur-3xl" />
        <div className="absolute -bottom-20 left-1/3 h-48 w-48 rounded-full bg-amber-300/12 blur-3xl" />
        <div className="relative grid gap-6 lg:grid-cols-[1.05fr_0.95fr] lg:items-center">
          <div className="space-y-5">
            <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/8 px-3 py-1.5 text-xs font-medium text-teal-100">
              <span className="signal-pulse size-2 rounded-full bg-teal-300" />
              Cockpit em tempo real
            </div>
            <div>
              <h2 className="max-w-2xl text-3xl font-semibold tracking-normal sm:text-4xl">
                Priorize receita, sincronização e próximos movimentos em uma única visão.
              </h2>
              <p className="mt-3 max-w-2xl text-sm leading-6 text-white/58">
                A Home agora funciona como sala de comando: indicadores principais, saúde do
                pipeline e sinais que orientam ações comerciais.
              </p>
            </div>
            <div className="grid gap-3 sm:grid-cols-3">
              <CockpitSignal label="Receita" value={formatCurrency(overview.data?.total_revenue)} icon={Wallet} />
              <CockpitSignal label="Pedidos" value={formatNumber(overview.data?.total_orders)} icon={ReceiptText} />
              <CockpitSignal label="Clientes" value={formatNumber(overview.data?.unique_customers)} icon={Users} />
            </div>
          </div>

          <div className="rounded-2xl border border-white/10 bg-white/[0.075] p-4 shadow-2xl shadow-black/20 backdrop-blur-xl">
            <div className="mb-4 flex items-center justify-between">
              <div>
                <p className="text-xs text-white/45">Fila de decisão</p>
                <p className="text-lg font-semibold">Próximas ações</p>
              </div>
              <div className="flex size-10 items-center justify-center rounded-2xl bg-teal-300 text-slate-950">
                <Sparkles className="size-5" />
              </div>
            </div>
            <div className="space-y-3">
              <ActionSignal label="Atualizar grafo" value="Base preparada para algoritmos" progress="w-[78%]" />
              <ActionSignal label="Revisar clientes" value="Segmentos RFM aguardando leitura" progress="w-[62%]" tone="bg-blue-400" />
              <ActionSignal label="Cross-sell" value="Produtos relacionados prontos para recomendação" progress="w-[54%]" tone="bg-amber-300" />
            </div>
            <div className="mt-4 grid gap-2 sm:grid-cols-2">
              <HeroActionButton
                label="Sincronizar ERP"
                icon={RefreshCw}
                loading={syncIntegration.isPending}
                disabled={!firstActiveIntegration}
                onClick={() => firstActiveIntegration && syncIntegration.mutate(firstActiveIntegration.integration_id)}
              />
              <HeroActionButton
                label="Projetar grafo"
                icon={GitBranch}
                loading={graphSync.isPending}
                onClick={() => graphSync.mutate()}
              />
              <HeroActionButton
                label="Rodar algoritmos"
                icon={Play}
                loading={algorithms.isPending}
                onClick={() => algorithms.mutate()}
              />
              <HeroActionButton
                label="Atualizar embeddings"
                icon={Sparkles}
                loading={embeddings.isPending}
                onClick={() => embeddings.mutate()}
              />
            </div>
          </div>
        </div>
      </section>

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-5">
        <StatCard
          label="Faturamento total"
          value={formatCurrency(overview.data?.total_revenue)}
          icon={Wallet}
          loading={overview.isLoading}
          tone="teal"
        />
        <StatCard
          label="Total de pedidos"
          value={formatNumber(overview.data?.total_orders)}
          icon={ReceiptText}
          loading={overview.isLoading}
          tone="blue"
        />
        <StatCard
          label="Ticket médio"
          value={formatCurrency(overview.data?.average_ticket)}
          icon={Wallet}
          loading={overview.isLoading}
          tone="amber"
        />
        <StatCard
          label="Clientes compradores"
          value={formatNumber(overview.data?.unique_customers)}
          icon={Users}
          loading={overview.isLoading}
          tone="violet"
        />
        <StatCard
          label="Produtos vendidos"
          value={formatNumber(overview.data?.products_sold)}
          icon={Package}
          loading={overview.isLoading}
          tone="rose"
        />
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <SectionCard title="Pedidos por status" icon={ReceiptText} className="lg:col-span-2">
            {overview.isLoading ? (
              <div className="h-64 animate-pulse rounded-md bg-muted" />
            ) : statusData.length === 0 ? (
              <EmptyState
                title="Sem pedidos ainda"
                description="Sincronize uma integração em Configurações > Integrações para ver os status aqui."
              />
            ) : (
              <ResponsiveContainer width="100%" height={260}>
                <BarChart data={statusData} layout="vertical" margin={{ left: 8 }}>
                  <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                  <XAxis type="number" allowDecimals={false} fontSize={12} />
                  <YAxis type="category" dataKey="status" width={90} fontSize={12} />
                  <Tooltip
                    formatter={(value) => [formatNumber(Number(value)), 'Pedidos']}
                    cursor={{ fill: 'var(--muted)' }}
                  />
                  <Bar dataKey="count" radius={[0, 4, 4, 0]}>
                    {statusData.map((entry) => (
                      <Cell key={entry.key} fill={entry.color} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            )}
        </SectionCard>

        <div className="space-y-4">
          <SectionCard title="Última sincronização" icon={Database}>
              <p className="text-lg font-semibold">
                <RelativeTime value={overview.data?.last_order_sync_at} />
              </p>
              <p className="mt-1 text-xs text-muted-foreground">Pedidos do ERP → Postgres</p>
          </SectionCard>
          <SectionCard title="Última execução dos algoritmos" icon={Play}>
              <p className="text-lg font-semibold">
                <RelativeTime value={overview.data?.last_algorithms_run_at} />
              </p>
              <p className="mt-1 text-xs text-muted-foreground">
                {(syncStatus.data?.algorithm_runs ?? []).length} job(s) já registrado(s)
              </p>
          </SectionCard>
        </div>
      </div>
    </div>
  )
}

function CockpitSignal({
  label,
  value,
  icon: Icon,
}: {
  label: string
  value: string
  icon: typeof Gauge
}) {
  return (
    <div className="rounded-2xl border border-white/10 bg-white/[0.07] p-3">
      <div className="flex items-center justify-between gap-3">
        <p className="text-xs text-white/48">{label}</p>
        <Icon className="size-4 text-teal-200" />
      </div>
      <p className="mt-2 truncate text-lg font-semibold">{value}</p>
    </div>
  )
}

function ActionSignal({
  label,
  value,
  progress,
  tone = 'bg-teal-300',
}: {
  label: string
  value: string
  progress: string
  tone?: string
}) {
  return (
    <div className="rounded-2xl border border-white/10 bg-white/[0.06] p-3">
      <div className="flex items-center justify-between gap-3 text-sm">
        <span className="font-medium">{label}</span>
        <TrendingUp className="size-4 text-white/45" />
      </div>
      <p className="mt-1 truncate text-xs text-white/45">{value}</p>
      <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-white/10">
        <div className={`progress-breathe h-full rounded-full ${tone} ${progress}`} />
      </div>
    </div>
  )
}

function HeroActionButton({
  label,
  icon: Icon,
  loading,
  disabled,
  onClick,
}: {
  label: string
  icon: typeof RefreshCw
  loading?: boolean
  disabled?: boolean
  onClick: () => void
}) {
  return (
    <Button
      type="button"
      className="justify-start rounded-2xl border border-white/10 bg-white/[0.08] text-white hover:bg-white/[0.14]"
      disabled={disabled || loading}
      onClick={onClick}
    >
      {loading ? <Loader2 className="size-4 animate-spin" /> : <Icon className="size-4" />}
      {label}
    </Button>
  )
}
