import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import {
  Database,
  Package,
  Play,
  ReceiptText,
  Users,
  Wallet,
  Workflow,
} from 'lucide-react'
import { StatCard } from '@/components/shared/StatCard'
import { RelativeTime } from '@/components/shared/RelativeTime'
import { EmptyState } from '@/components/shared/EmptyState'
import { PageHeader } from '@/components/shared/PageHeader'
import { SectionCard } from '@/components/shared/SectionCard'
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

  const statusData = (overview.data?.orders_by_status ?? []).map((item) => ({
    key: item.status,
    status: STATUS_LABELS[item.status] ?? item.status,
    count: item.count,
    color: STATUS_COLORS[item.status] ?? '#64748b',
  }))

  return (
    <div className="space-y-6">
      <PageHeader
        title="Operação comercial"
        description="Acompanhe a saúde do pipeline e os principais indicadores da empresa."
        icon={Workflow}
      />

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
