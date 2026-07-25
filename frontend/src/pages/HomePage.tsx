import { useState } from 'react'
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import {
  Database,
  Loader2,
  Package,
  Play,
  ReceiptText,
  RefreshCw,
  Sparkles,
  Users,
  Wallet,
  Workflow,
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { StatCard } from '@/components/shared/StatCard'
import { RelativeTime } from '@/components/shared/RelativeTime'
import { EmptyState } from '@/components/shared/EmptyState'
import { useOverview, useSyncStatus } from '@/hooks/use-dashboard'
import { useIntegrations } from '@/hooks/use-catalog'
import {
  useGraphSyncAction,
  useRunAlgorithmsAction,
  useRunEmbeddingsAction,
  useSyncIntegrationAction,
} from '@/hooks/use-actions'
import { formatCurrency, formatNumber } from '@/lib/format'

const STATUS_LABELS: Record<string, string> = {
  paid: 'Pago',
  pending: 'Pendente',
  canceled: 'Cancelado',
  cancelled: 'Cancelado',
  shipped: 'Enviado',
  delivered: 'Entregue',
}

export function HomePage() {
  const overview = useOverview()
  const syncStatus = useSyncStatus()
  const integrations = useIntegrations()
  const [selectedIntegration, setSelectedIntegration] = useState<string>('')

  const syncAction = useSyncIntegrationAction()
  const graphSyncAction = useGraphSyncAction()
  const algorithmsAction = useRunAlgorithmsAction()
  const embeddingsAction = useRunEmbeddingsAction()

  const statusData = (overview.data?.orders_by_status ?? []).map((item) => ({
    status: STATUS_LABELS[item.status] ?? item.status,
    count: item.count,
  }))

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium">Ações</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-wrap items-center gap-2">
          <Select value={selectedIntegration} onValueChange={setSelectedIntegration}>
            <SelectTrigger className="w-56">
              <SelectValue placeholder="Selecione uma integração" />
            </SelectTrigger>
            <SelectContent>
              {(integrations.data ?? []).map((integration) => (
                <SelectItem key={integration.id} value={integration.id}>
                  {integration.name} ({integration.provider})
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button
            variant="outline"
            disabled={!selectedIntegration || syncAction.isPending}
            onClick={() => syncAction.mutate(selectedIntegration)}
          >
            {syncAction.isPending ? (
              <Loader2 className="size-4 animate-spin" />
            ) : (
              <RefreshCw className="size-4" />
            )}
            Sincronizar pedidos
          </Button>
          <Button
            variant="outline"
            disabled={graphSyncAction.isPending}
            onClick={() => graphSyncAction.mutate()}
          >
            {graphSyncAction.isPending ? (
              <Loader2 className="size-4 animate-spin" />
            ) : (
              <Workflow className="size-4" />
            )}
            Projetar no grafo
          </Button>
          <Button
            variant="outline"
            disabled={algorithmsAction.isPending}
            onClick={() => algorithmsAction.mutate()}
          >
            {algorithmsAction.isPending ? (
              <Loader2 className="size-4 animate-spin" />
            ) : (
              <Play className="size-4" />
            )}
            Rodar algoritmos
          </Button>
          <Button
            variant="outline"
            disabled={embeddingsAction.isPending}
            onClick={() => embeddingsAction.mutate()}
          >
            {embeddingsAction.isPending ? (
              <Loader2 className="size-4 animate-spin" />
            ) : (
              <Sparkles className="size-4" />
            )}
            Rodar embeddings
          </Button>
        </CardContent>
      </Card>

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-5">
        <StatCard
          label="Faturamento total"
          value={formatCurrency(overview.data?.total_revenue)}
          icon={Wallet}
          loading={overview.isLoading}
        />
        <StatCard
          label="Total de pedidos"
          value={formatNumber(overview.data?.total_orders)}
          icon={ReceiptText}
          loading={overview.isLoading}
        />
        <StatCard
          label="Ticket médio"
          value={formatCurrency(overview.data?.average_ticket)}
          icon={Wallet}
          loading={overview.isLoading}
        />
        <StatCard
          label="Clientes compradores"
          value={formatNumber(overview.data?.unique_customers)}
          icon={Users}
          loading={overview.isLoading}
        />
        <StatCard
          label="Produtos vendidos"
          value={formatNumber(overview.data?.products_sold)}
          icon={Package}
          loading={overview.isLoading}
        />
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="text-sm font-medium">Pedidos por status</CardTitle>
          </CardHeader>
          <CardContent>
            {overview.isLoading ? (
              <div className="h-64 animate-pulse rounded-md bg-muted" />
            ) : statusData.length === 0 ? (
              <EmptyState
                title="Sem pedidos ainda"
                description="Sincronize uma integração para ver os status aqui."
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
                  <Bar dataKey="count" fill="var(--primary)" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>

        <div className="space-y-4">
          <Card>
            <CardHeader className="flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium">Última sincronização</CardTitle>
              <Database className="size-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <p className="text-lg font-semibold">
                <RelativeTime value={overview.data?.last_order_sync_at} />
              </p>
              <p className="mt-1 text-xs text-muted-foreground">Pedidos do ERP → Postgres</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium">Última execução dos algoritmos</CardTitle>
              <Play className="size-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <p className="text-lg font-semibold">
                <RelativeTime value={overview.data?.last_algorithms_run_at} />
              </p>
              <p className="mt-1 text-xs text-muted-foreground">
                {(syncStatus.data?.algorithm_runs ?? []).length} job(s) já registrado(s)
              </p>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}
