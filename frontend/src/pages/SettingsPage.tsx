import { useEffect, useMemo, useState } from 'react'
import type { FormEvent, ReactNode } from 'react'
import {
  Building2,
  CheckCircle2,
  Clock,
  Database,
  Fingerprint,
  Loader2,
  Pencil,
  Play,
  PlugZap,
  Power,
  Plus,
  RefreshCw,
  Sparkles,
  Trash2,
  Workflow,
  X,
} from 'lucide-react'
import { toast } from 'sonner'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Textarea } from '@/components/ui/textarea'
import { EmptyState } from '@/components/shared/EmptyState'
import { PageHeader } from '@/components/shared/PageHeader'
import { RelativeTime } from '@/components/shared/RelativeTime'
import { SectionCard } from '@/components/shared/SectionCard'
import {
  useBrandArchetypeProfiles,
  useCompanies,
  useCreateBrandArchetypeProfile,
  useCreateIntegration,
  useDeleteBrandArchetypeProfile,
  useDeleteIntegration,
  useIntegrations,
  useUpdateBrandArchetypeProfile,
  useUpdateIntegration,
} from '@/hooks/use-catalog'
import { useSyncStatus } from '@/hooks/use-dashboard'
import {
  useGraphSyncAction,
  useRunAlgorithmsAction,
  useRunEmbeddingsAction,
  useSyncIntegrationAction,
} from '@/hooks/use-actions'
import { formatDateTime } from '@/lib/format'
import { archetypeLabel, BRAND_ARCHETYPES } from '@/lib/brand-archetypes'
import type {
  BrandArchetype,
  BrandArchetypeProfile,
  BrandArchetypeProfileCreateInput,
  Company,
  Integration,
  IntegrationSyncStatus,
} from '@/types/api'

type KeyValueType = 'string' | 'number' | 'boolean' | 'json' | 'null'

type KeyValueRow = {
  id: string
  key: string
  value: string
  type: KeyValueType
}

function inferValueType(value: unknown): KeyValueType {
  if (value === null) return 'null'
  if (typeof value === 'boolean') return 'boolean'
  if (typeof value === 'number') return 'number'
  if (typeof value === 'object') return 'json'
  return 'string'
}

function valueToInput(value: unknown) {
  if (value === null) return ''
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
}

function objectToRows(value: Record<string, unknown>) {
  const entries = Object.entries(value ?? {})
  if (entries.length === 0) {
    return [{ id: crypto.randomUUID(), key: '', value: '', type: 'string' as const }]
  }
  return entries.map(([key, entryValue]) => ({
    id: crypto.randomUUID(),
    key,
    value: valueToInput(entryValue),
    type: inferValueType(entryValue),
  }))
}

function rowsToObject(rows: KeyValueRow[], label: string) {
  const output: Record<string, unknown> = {}
  for (const row of rows) {
    const key = row.key.trim()
    if (!key && !row.value.trim()) continue
    if (!key) throw new Error(`${label}: existe uma linha sem chave.`)
    if (Object.hasOwn(output, key)) throw new Error(`${label}: chave duplicada "${key}".`)
    output[key] = parseRowValue(row, label)
  }
  return output
}

function parseRowValue(row: KeyValueRow, label: string) {
  const value = row.value.trim()
  if (row.type === 'string') return row.value
  if (row.type === 'null') return null
  if (row.type === 'boolean') return value === 'true'
  if (row.type === 'number') {
    const number = Number(value)
    if (Number.isNaN(number)) {
      throw new Error(`${label}: "${row.key}" precisa ser um número.`)
    }
    return number
  }
  try {
    return JSON.parse(value || 'null')
  } catch {
    throw new Error(`${label}: "${row.key}" não contém JSON válido.`)
  }
}

function addEmptyRow(rows: KeyValueRow[]) {
  return [...rows, { id: crypto.randomUUID(), key: '', value: '', type: 'string' as const }]
}

export function SettingsPage() {
  const companies = useCompanies()
  const integrations = useIntegrations()
  const company = companies.data?.[0]
  const activeIntegrations = useMemo(
    () => (integrations.data ?? []).filter((integration) => integration.is_active).length,
    [integrations.data],
  )

  return (
    <div className="space-y-6">
      <PageHeader
        title="Configurações"
        description="Gerencie o perfil da empresa e as integrações usadas pela camada autenticada."
        icon={Building2}
      />

      <Tabs defaultValue="company">
        <TabsList>
          <TabsTrigger value="company">Empresa</TabsTrigger>
          <TabsTrigger value="integrations">Integrações</TabsTrigger>
          <TabsTrigger value="brand-archetype">Arquétipo de marca</TabsTrigger>
        </TabsList>

        <TabsContent value="company" className="mt-4">
          <SectionCard
            title="Perfil da empresa"
            description="Dados usados para isolar consultas, pedidos, grafo e integrações."
            icon={Building2}
          >
              {companies.isLoading ? (
                <div className="h-40 animate-pulse rounded-lg bg-muted" />
              ) : company ? (
                <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
                  <InfoTile label="Nome" value={company.name} />
                  <InfoTile label="Domain ID" value={String(company.domain_id)} />
                  <InfoTile label="Company interna" value={company.id} mono />
                  <InfoTile label="Company ERP" value={company.external_company_id} mono />
                  <InfoTile
                    label="Status"
                    value={company.is_active ? 'Ativa' : 'Inativa'}
                    tone={company.is_active ? 'success' : 'muted'}
                  />
                  <InfoTile label="Criada" value={<RelativeTime value={company.created_at} />} />
                  <InfoTile label="Atualizada" value={<RelativeTime value={company.updated_at} />} />
                  <InfoTile label="Integrações ativas" value={String(activeIntegrations)} />
                </div>
              ) : (
                <EmptyState
                  title="Empresa não encontrada"
                  description="O usuário autenticado não retornou uma empresa ativa."
                />
              )}
          </SectionCard>
        </TabsContent>

        <TabsContent value="integrations" className="mt-4">
          <IntegrationsSettings
            company={company}
            integrations={integrations.data}
            loading={integrations.isLoading}
          />
        </TabsContent>

        <TabsContent value="brand-archetype" className="mt-4">
          <BrandArchetypeSettings company={company} companyLoading={companies.isLoading} />
        </TabsContent>
      </Tabs>
    </div>
  )
}

function InfoTile({
  label,
  value,
  mono,
  tone,
}: {
  label: string
  value: ReactNode
  mono?: boolean
  tone?: 'success' | 'muted'
}) {
  return (
    <div className="min-w-0 rounded-lg border bg-card p-3 shadow-sm">
      <p className="text-xs font-medium text-muted-foreground">{label}</p>
      <div
        className={[
          'mt-1 truncate text-sm font-medium',
          mono ? 'font-mono text-xs' : '',
          tone === 'success' ? 'text-emerald-700 dark:text-emerald-400' : '',
          tone === 'muted' ? 'text-muted-foreground' : '',
        ].join(' ')}
        title={typeof value === 'string' ? value : undefined}
      >
        {value}
      </div>
    </div>
  )
}

const SYNC_STATUS_META: Record<string, { label: string; className: string }> = {
  running: {
    label: 'Sincronizando',
    className: 'border-amber-200 bg-amber-50 text-amber-700',
  },
  idle: {
    label: 'Em dia',
    className: 'border-emerald-200 bg-emerald-50 text-emerald-700',
  },
  never_synced: {
    label: 'Nunca sincronizado',
    className: 'border-slate-200 bg-slate-100 text-slate-600',
  },
}

const RESOURCE_LABELS: Record<string, string> = {
  orders: 'Pedidos',
  products: 'Produtos',
}

function integrationResources(integration: Integration): string[] {
  const resources = integration.params.resources
  if (Array.isArray(resources)) {
    const values = resources.filter((resource): resource is string => typeof resource === 'string')
    return values.length > 0 ? values : ['orders']
  }
  return ['orders']
}

function integrationEditableParams(integration: Integration): Record<string, unknown> {
  const params = { ...integration.params }
  delete params.resources
  return params
}

function IntegrationsSettings({
  company,
  integrations,
  loading,
}: {
  company: Company | undefined
  integrations: Integration[] | undefined
  loading?: boolean
}) {
  const [creating, setCreating] = useState(false)
  const [editing, setEditing] = useState<Integration | null>(null)
  const [deleting, setDeleting] = useState<Integration | null>(null)
  const deleteIntegration = useDeleteIntegration()
  const syncIntegration = useSyncIntegrationAction()
  const graphSyncAction = useGraphSyncAction()
  const algorithmsAction = useRunAlgorithmsAction()
  const embeddingsAction = useRunEmbeddingsAction()
  const syncStatus = useSyncStatus()
  const syncStatusByIntegrationId = useMemo(() => {
    const entries = syncStatus.data?.integrations ?? []
    return new Map<string, IntegrationSyncStatus>(entries.map((entry) => [entry.integration_id, entry]))
  }, [syncStatus.data])

  return (
    <>
      <SectionCard
        title="Pipeline de dados"
        description="Sincronize integrações, projete dados no grafo e atualize os sinais comerciais."
        icon={Database}
        className="mb-4"
      >
        <div className="flex flex-wrap items-center gap-2.5">
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
        </div>
      </SectionCard>

      <SectionCard
        title="Integrações"
        description="Atualize credenciais, parâmetros e status das conexões ERP."
        icon={PlugZap}
        actions={
          company ? (
            <Button size="sm" onClick={() => setCreating(true)}>
              <Plus className="size-4" />
              Nova integração
            </Button>
          ) : null
        }
      >
          {loading ? (
            <div className="h-48 animate-pulse rounded-lg bg-muted" />
          ) : !integrations || integrations.length === 0 ? (
            <EmptyState title="Nenhuma integração cadastrada" />
          ) : (
            <div className="grid gap-3">
              {integrations.map((integration) => {
                const status = syncStatusByIntegrationId.get(integration.id)
                const statusMeta =
                  SYNC_STATUS_META[status?.status ?? 'never_synced'] ?? SYNC_STATUS_META.never_synced
                return (
                <div
                  key={integration.id}
                  className="grid gap-3 rounded-lg border bg-card p-4 shadow-sm lg:grid-cols-[1fr_auto]"
                >
                  <div className="min-w-0 space-y-2">
                    <div className="flex flex-wrap items-center gap-2">
                      <h3 className="truncate text-sm font-semibold">{integration.name}</h3>
                      <Badge variant="outline">{integration.provider}</Badge>
                      {integrationResources(integration).map((resource) => (
                        <Badge key={resource} variant="outline">
                          {RESOURCE_LABELS[resource] ?? resource}
                        </Badge>
                      ))}
                      <Badge
                        variant="outline"
                        className={
                          integration.is_active
                            ? 'border-emerald-200 bg-emerald-50 text-emerald-700'
                            : 'border-slate-200 bg-slate-100 text-slate-600'
                        }
                      >
                        {integration.is_active ? 'Ativa' : 'Inativa'}
                      </Badge>
                      <Badge variant="outline" className={statusMeta.className}>
                        {status?.status === 'running' ? (
                          <Loader2 className="size-3 animate-spin" />
                        ) : (
                          <Clock className="size-3" />
                        )}
                        {statusMeta.label}
                      </Badge>
                    </div>
                    <p className="truncate font-mono text-xs text-muted-foreground">
                      {integration.base_url}
                    </p>
                    <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
                      <span>ID {integration.id}</span>
                      <span>
                        Atualizada <RelativeTime value={integration.updated_at} />
                      </span>
                      <span>
                        Última sincronização <RelativeTime value={status?.last_synced_at} />
                      </span>
                      <span>
                        Pedidos sincronizados até{' '}
                        {status?.synced_until ? formatDateTime(status.synced_until) : '—'}
                      </span>
                    </div>
                    {status?.resource_statuses?.length ? (
                      <div className="flex flex-wrap gap-1.5">
                        {status.resource_statuses.map((resourceStatus) => {
                          const resourceMeta =
                            SYNC_STATUS_META[resourceStatus.status] ?? SYNC_STATUS_META.never_synced
                          return (
                            <Badge
                              key={resourceStatus.resource}
                              variant="outline"
                              className={resourceMeta.className}
                            >
                              {RESOURCE_LABELS[resourceStatus.resource] ?? resourceStatus.resource}:{' '}
                              {resourceMeta.label}
                            </Badge>
                          )
                        })}
                      </div>
                    ) : null}
                  </div>
                  <div className="flex items-center gap-2 lg:justify-end">
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={!integration.is_active || syncIntegration.isPending}
                      onClick={() => syncIntegration.mutate(integration.id)}
                    >
                      {syncIntegration.isPending &&
                      syncIntegration.variables === integration.id ? (
                        <Loader2 className="size-4 animate-spin" />
                      ) : (
                        <RefreshCw className="size-4" />
                      )}
                      Sincronizar
                    </Button>
                    <Button variant="outline" size="sm" onClick={() => setEditing(integration)}>
                      <Pencil className="size-4" />
                      Editar
                    </Button>
                    <Button
                      variant="destructive"
                      size="sm"
                      onClick={() => setDeleting(integration)}
                    >
                      <Trash2 className="size-4" />
                      Excluir
                    </Button>
                  </div>
                </div>
                )
              })}
            </div>
          )}
      </SectionCard>

      <IntegrationCreateSheet
        company={company ?? null}
        open={creating}
        onClose={() => setCreating(false)}
      />
      <IntegrationEditSheet integration={editing} onClose={() => setEditing(null)} />

      <Dialog open={Boolean(deleting)} onOpenChange={(open) => !open && setDeleting(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Excluir integração</DialogTitle>
            <DialogDescription>
              Esta ação remove a integração e os pedidos vinculados a ela no Postgres.
            </DialogDescription>
          </DialogHeader>
          <p className="text-sm">
            Confirma a exclusão de <strong>{deleting?.name}</strong>?
          </p>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleting(null)}>
              Cancelar
            </Button>
            <Button
              variant="destructive"
              disabled={deleteIntegration.isPending}
              onClick={() => {
                if (!deleting) return
                deleteIntegration.mutate(deleting.id, {
                  onSuccess: () => setDeleting(null),
                })
              }}
            >
              {deleteIntegration.isPending ? (
                <Loader2 className="size-4 animate-spin" />
              ) : (
                <Trash2 className="size-4" />
              )}
              Excluir
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}

function IntegrationCreateSheet({
  company,
  open,
  onClose,
}: {
  company: Company | null
  open: boolean
  onClose: () => void
}) {
  const createIntegration = useCreateIntegration()
  const [name, setName] = useState('Vesti')
  const [baseUrl, setBaseUrl] = useState('')
  const [apikey, setApikey] = useState('')
  const [backfillStartDate, setBackfillStartDate] = useState('')
  const [windowDays, setWindowDays] = useState('28')
  const [syncOrders, setSyncOrders] = useState(true)
  const [syncProducts, setSyncProducts] = useState(true)
  const [isActive, setIsActive] = useState(true)

  useEffect(() => {
    if (!open) return
    setName('Vesti')
    setBaseUrl('')
    setApikey('')
    setBackfillStartDate('')
    setWindowDays('28')
    setSyncOrders(true)
    setSyncProducts(true)
    setIsActive(true)
  }, [open])

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!company) return
    const resources = [
      ...(syncOrders ? ['orders'] : []),
      ...(syncProducts ? ['products'] : []),
    ]
    if (resources.length === 0) {
      toast.error('Selecione ao menos um recurso')
      return
    }

    const parsedWindowDays = Number(windowDays)
    if (!Number.isInteger(parsedWindowDays) || parsedWindowDays < 1 || parsedWindowDays > 31) {
      toast.error('Janela inválida', {
        description: 'Use um número inteiro entre 1 e 31 dias.',
      })
      return
    }

    createIntegration.mutate(
      {
        company_id: company.id,
        provider: 'vesti',
        name,
        base_url: baseUrl,
        configs: { apikey },
        params: {
          backfill_start_date: backfillStartDate,
          window_days: parsedWindowDays,
          resources,
        },
        is_active: isActive,
      },
      { onSuccess: onClose },
    )
  }

  return (
    <Sheet open={open} onOpenChange={(nextOpen) => !nextOpen && onClose()}>
      <SheetContent className="overflow-y-auto data-[side=right]:w-full data-[side=right]:sm:max-w-none data-[side=right]:lg:w-[42vw]">
        <SheetHeader>
          <SheetTitle>Nova integração Vesti</SheetTitle>
          <SheetDescription>
            Cadastre a URL da API, token e quais recursos serão sincronizados.
          </SheetDescription>
        </SheetHeader>

        <form className="space-y-4 px-4 pb-6" onSubmit={onSubmit}>
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="new-integration-name">Nome</Label>
              <Input
                id="new-integration-name"
                value={name}
                onChange={(event) => setName(event.target.value)}
                required
              />
            </div>
            <div className="space-y-2">
              <Label>Provider</Label>
              <Input value="vesti" disabled />
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="new-integration-base-url">Base URL</Label>
            <Input
              id="new-integration-base-url"
              value={baseUrl}
              onChange={(event) => setBaseUrl(event.target.value)}
              placeholder="https://api.exemplo.com"
              required
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="new-integration-apikey">API key</Label>
            <Input
              id="new-integration-apikey"
              type="password"
              value={apikey}
              onChange={(event) => setApikey(event.target.value)}
              required
            />
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="new-integration-backfill">Início do histórico</Label>
              <Input
                id="new-integration-backfill"
                type="date"
                value={backfillStartDate}
                onChange={(event) => setBackfillStartDate(event.target.value)}
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="new-integration-window-days">Janela em dias</Label>
              <Input
                id="new-integration-window-days"
                type="number"
                min={1}
                max={31}
                value={windowDays}
                onChange={(event) => setWindowDays(event.target.value)}
                required
              />
            </div>
          </div>

          <section className="space-y-3 rounded-lg border bg-card p-3 shadow-sm">
            <h3 className="text-sm font-medium">Recursos</h3>
            <div className="grid gap-2 sm:grid-cols-2">
              <label className="flex items-center gap-2 rounded-lg border bg-muted/35 p-3 text-sm">
                <input
                  type="checkbox"
                  checked={syncOrders}
                  onChange={(event) => setSyncOrders(event.target.checked)}
                  className="size-4 accent-primary"
                />
                Pedidos
              </label>
              <label className="flex items-center gap-2 rounded-lg border bg-muted/35 p-3 text-sm">
                <input
                  type="checkbox"
                  checked={syncProducts}
                  onChange={(event) => setSyncProducts(event.target.checked)}
                  className="size-4 accent-primary"
                />
                Produtos
              </label>
            </div>
          </section>

          <label className="flex items-center gap-2 rounded-lg border bg-muted/35 p-3 text-sm">
            <input
              type="checkbox"
              checked={isActive}
              onChange={(event) => setIsActive(event.target.checked)}
              className="size-4 accent-primary"
            />
            <Power className="size-4 text-primary" />
            Integração ativa
          </label>

          <div className="sticky bottom-0 -mx-4 flex justify-end gap-2 border-t bg-popover/95 p-4 backdrop-blur">
            <Button type="button" variant="outline" onClick={onClose}>
              Cancelar
            </Button>
            <Button disabled={createIntegration.isPending}>
              {createIntegration.isPending ? (
                <Loader2 className="size-4 animate-spin" />
              ) : (
                <CheckCircle2 className="size-4" />
              )}
              Criar integração
            </Button>
          </div>
        </form>
      </SheetContent>
    </Sheet>
  )
}

function IntegrationEditSheet({
  integration,
  onClose,
}: {
  integration: Integration | null
  onClose: () => void
}) {
  const updateIntegration = useUpdateIntegration()
  const [name, setName] = useState('')
  const [baseUrl, setBaseUrl] = useState('')
  const [configs, setConfigs] = useState<KeyValueRow[]>(() => addEmptyRow([]))
  const [params, setParams] = useState<KeyValueRow[]>(() => addEmptyRow([]))
  const [syncOrders, setSyncOrders] = useState(true)
  const [syncProducts, setSyncProducts] = useState(false)
  const [isActive, setIsActive] = useState(true)

  useEffect(() => {
    if (!integration) return
    setName(integration.name)
    setBaseUrl(integration.base_url)
    setConfigs(objectToRows(integration.configs))
    setParams(objectToRows(integrationEditableParams(integration)))
    const resources = integrationResources(integration)
    setSyncOrders(resources.includes('orders'))
    setSyncProducts(resources.includes('products'))
    setIsActive(integration.is_active)
  }, [integration])

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!integration) return

    try {
      const parsedConfigs = rowsToObject(configs, 'Configs')
      const parsedParams = rowsToObject(params, 'Params')
      const resources = [
        ...(syncOrders ? ['orders'] : []),
        ...(syncProducts ? ['products'] : []),
      ]
      if (resources.length === 0) {
        toast.error('Selecione ao menos um recurso')
        return
      }
      parsedParams.resources = resources
      updateIntegration.mutate(
        {
          id: integration.id,
          data: {
            name,
            base_url: baseUrl,
            configs: parsedConfigs,
            params: parsedParams,
            is_active: isActive,
          },
        },
        { onSuccess: onClose },
      )
    } catch (error) {
      toast.error('Campos inválidos', {
        description: error instanceof Error ? error.message : 'Revise as chaves e valores.',
      })
    }
  }

  return (
    <Sheet open={Boolean(integration)} onOpenChange={(open) => !open && onClose()}>
      <SheetContent className="overflow-y-auto data-[side=right]:w-full data-[side=right]:sm:max-w-none data-[side=right]:lg:w-[50vw]">
        <SheetHeader>
          <SheetTitle>Editar integração</SheetTitle>
          <SheetDescription>
            Atualize nome, endpoint, credenciais, parâmetros e status.
          </SheetDescription>
        </SheetHeader>

        <form className="space-y-4 px-4 pb-6" onSubmit={onSubmit}>
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="integration-name">Nome</Label>
              <Input
                id="integration-name"
                value={name}
                onChange={(event) => setName(event.target.value)}
                required
              />
            </div>
            <div className="space-y-2">
              <Label>Provider</Label>
              <Input value={integration?.provider ?? ''} disabled />
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="integration-base-url">Base URL</Label>
            <Input
              id="integration-base-url"
              value={baseUrl}
              onChange={(event) => setBaseUrl(event.target.value)}
              required
            />
          </div>

          <label className="flex items-center gap-2 rounded-lg border bg-muted/35 p-3 text-sm">
            <input
              type="checkbox"
              checked={isActive}
              onChange={(event) => setIsActive(event.target.checked)}
              className="size-4 accent-primary"
            />
            <Power className="size-4 text-primary" />
            Integração ativa
          </label>

          <KeyValueEditor
            title="Configs"
            description="Credenciais e dados sensíveis enviados como objeto JSON."
            rows={configs}
            onChange={setConfigs}
            sensitive
          />

          <KeyValueEditor
            title="Params"
            description="Parâmetros não secretos de sincronização e comportamento."
            rows={params}
            onChange={setParams}
          />

          <section className="space-y-3 rounded-lg border bg-card p-3 shadow-sm">
            <h3 className="text-sm font-medium">Recursos sincronizados</h3>
            <div className="grid gap-2 sm:grid-cols-2">
              <label className="flex items-center gap-2 rounded-lg border bg-muted/35 p-3 text-sm">
                <input
                  type="checkbox"
                  checked={syncOrders}
                  onChange={(event) => setSyncOrders(event.target.checked)}
                  className="size-4 accent-primary"
                />
                Pedidos
              </label>
              <label className="flex items-center gap-2 rounded-lg border bg-muted/35 p-3 text-sm">
                <input
                  type="checkbox"
                  checked={syncProducts}
                  onChange={(event) => setSyncProducts(event.target.checked)}
                  className="size-4 accent-primary"
                />
                Produtos
              </label>
            </div>
          </section>

          <div className="sticky bottom-0 -mx-4 flex justify-end gap-2 border-t bg-popover/95 p-4 backdrop-blur">
            <Button type="button" variant="outline" onClick={onClose}>
              Cancelar
            </Button>
            <Button disabled={updateIntegration.isPending}>
              {updateIntegration.isPending ? (
                <Loader2 className="size-4 animate-spin" />
              ) : (
                <CheckCircle2 className="size-4" />
              )}
              Salvar alterações
            </Button>
          </div>
        </form>
      </SheetContent>
    </Sheet>
  )
}

function KeyValueEditor({
  title,
  description,
  rows,
  onChange,
  sensitive,
}: {
  title: string
  description: string
  rows: KeyValueRow[]
  onChange: (rows: KeyValueRow[]) => void
  sensitive?: boolean
}) {
  function updateRow(id: string, patch: Partial<KeyValueRow>) {
    onChange(rows.map((row) => (row.id === id ? { ...row, ...patch } : row)))
  }

  function removeRow(id: string) {
    const next = rows.filter((row) => row.id !== id)
    onChange(next.length > 0 ? next : addEmptyRow([]))
  }

  return (
    <section className="space-y-3 rounded-lg border bg-card p-3 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <h3 className="text-sm font-medium">{title}</h3>
          <p className="text-xs text-muted-foreground">{description}</p>
        </div>
        <Button type="button" variant="outline" size="sm" onClick={() => onChange(addEmptyRow(rows))}>
          <Plus className="size-4" />
          Adicionar
        </Button>
      </div>

      <div className="space-y-2">
        <div className="hidden grid-cols-[1fr_130px_1.4fr_32px] gap-2 px-1 text-xs font-medium text-muted-foreground md:grid">
          <span>Chave</span>
          <span>Tipo</span>
          <span>Valor</span>
          <span />
        </div>
        {rows.map((row) => (
          <div key={row.id} className="grid gap-2 rounded-lg border bg-muted/25 p-2 md:grid-cols-[1fr_130px_1.4fr_32px]">
            <Input
              value={row.key}
              onChange={(event) => updateRow(row.id, { key: event.target.value })}
              placeholder={sensitive ? 'apikey' : 'window_days'}
              className="font-mono text-xs"
            />
            <select
              value={row.type}
              onChange={(event) =>
                updateRow(row.id, { type: event.target.value as KeyValueType })
              }
              className="h-8 rounded-lg border border-input bg-background px-2 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
            >
              <option value="string">Texto</option>
              <option value="number">Número</option>
              <option value="boolean">Booleano</option>
              <option value="json">JSON</option>
              <option value="null">Null</option>
            </select>
            {row.type === 'boolean' ? (
              <select
                value={row.value === 'true' ? 'true' : 'false'}
                onChange={(event) => updateRow(row.id, { value: event.target.value })}
                className="h-8 rounded-lg border border-input bg-background px-2 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
              >
                <option value="true">true</option>
                <option value="false">false</option>
              </select>
            ) : row.type === 'null' ? (
              <Input value="null" disabled className="font-mono text-xs" />
            ) : (
              <Input
                value={row.value}
                type={sensitive && row.type === 'string' ? 'password' : 'text'}
                onChange={(event) => updateRow(row.id, { value: event.target.value })}
                placeholder={row.type === 'json' ? '{"key":"value"}' : 'valor'}
                className="font-mono text-xs"
              />
            )}
            <Button
              type="button"
              variant="ghost"
              size="icon"
              className="justify-self-end"
              onClick={() => removeRow(row.id)}
            >
              <X className="size-4" />
            </Button>
          </div>
        ))}
      </div>
    </section>
  )
}

function linesToArray(value: string): string[] {
  return value
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)
}

function arrayToLines(value: string[] | undefined): string {
  return (value ?? []).join('\n')
}

const NO_SECONDARY_ARCHETYPE = 'none'

function BrandArchetypeSettings({
  company,
  companyLoading,
}: {
  company: Company | undefined
  companyLoading?: boolean
}) {
  const profiles = useBrandArchetypeProfiles()
  const deleteProfile = useDeleteBrandArchetypeProfile()
  const [editingOpen, setEditingOpen] = useState(false)
  const [deleting, setDeleting] = useState(false)

  const profile = profiles.data?.[0]
  const loading = companyLoading || profiles.isLoading

  return (
    <>
      <SectionCard
        title="Arquétipo de marca"
        description="Personalidade e voz da marca — contexto reutilizado pelos futuros agentes de conteúdo (Oráculo Marketing, roteiro/vídeo)."
        icon={Fingerprint}
        actions={
          company ? (
            <div className="flex items-center gap-2">
              {profile ? (
                <Button variant="destructive" size="sm" onClick={() => setDeleting(true)}>
                  <Trash2 className="size-4" />
                  Excluir
                </Button>
              ) : null}
              <Button size="sm" onClick={() => setEditingOpen(true)}>
                {profile ? <Pencil className="size-4" /> : <Plus className="size-4" />}
                {profile ? 'Editar' : 'Criar perfil'}
              </Button>
            </div>
          ) : null
        }
      >
        {loading ? (
          <div className="h-40 animate-pulse rounded-lg bg-muted" />
        ) : !company ? (
          <EmptyState
            title="Empresa não encontrada"
            description="É preciso ter uma empresa ativa para configurar o arquétipo de marca."
          />
        ) : !profile ? (
          <EmptyState
            icon={Fingerprint}
            title="Nenhum arquétipo definido"
            description="Defina o arquétipo primário/secundário, voz, público e diretrizes de conteúdo desta marca."
          />
        ) : (
          <BrandArchetypeProfileView profile={profile} />
        )}
      </SectionCard>

      <BrandArchetypeProfileSheet
        open={editingOpen}
        company={company ?? null}
        profile={profile ?? null}
        onClose={() => setEditingOpen(false)}
      />

      <Dialog open={deleting} onOpenChange={setDeleting}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Excluir arquétipo de marca</DialogTitle>
            <DialogDescription>
              Remove o perfil de arquétipo desta empresa. Pode ser recriado depois.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleting(false)}>
              Cancelar
            </Button>
            <Button
              variant="destructive"
              disabled={deleteProfile.isPending}
              onClick={() => {
                if (!profile) return
                deleteProfile.mutate(profile.id, { onSuccess: () => setDeleting(false) })
              }}
            >
              {deleteProfile.isPending ? (
                <Loader2 className="size-4 animate-spin" />
              ) : (
                <Trash2 className="size-4" />
              )}
              Excluir
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}

function BrandArchetypeProfileView({ profile }: { profile: BrandArchetypeProfile }) {
  return (
    <div className="space-y-4">
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        <InfoTile label="Arquétipo primário" value={archetypeLabel(profile.primary_archetype)} />
        <InfoTile
          label="Arquétipo secundário"
          value={archetypeLabel(profile.secondary_archetype)}
        />
        <InfoTile label="Atualizado" value={<RelativeTime value={profile.updated_at} />} />
        <InfoTile label="Desejo central" value={profile.core_desire || '—'} />
        <InfoTile label="Medo" value={profile.fear || '—'} />
        <InfoTile label="Estratégia" value={profile.strategy || '—'} />
      </div>

      <div className="grid gap-3 lg:grid-cols-2">
        <section className="space-y-3 rounded-lg border bg-card p-3 shadow-sm">
          <h3 className="text-sm font-medium">Voz</h3>
          <div className="space-y-2 text-xs">
            <div>
              <p className="mb-1 font-medium text-muted-foreground">Tom</p>
              <TagList items={profile.voice.tone} />
            </div>
            <InfoRow label="Estilo de frase" value={profile.voice.sentence_style} />
            <div>
              <p className="mb-1 font-medium text-muted-foreground">Vocabulário preferido</p>
              <TagList items={profile.voice.vocabulary_prefer} tone="positive" />
            </div>
            <div>
              <p className="mb-1 font-medium text-muted-foreground">Vocabulário a evitar</p>
              <TagList items={profile.voice.vocabulary_avoid} tone="negative" />
            </div>
          </div>
        </section>

        <section className="space-y-3 rounded-lg border bg-card p-3 shadow-sm">
          <h3 className="text-sm font-medium">Público</h3>
          <div className="space-y-2 text-xs">
            <InfoRow label="Quem é" value={profile.audience.who} />
            <InfoRow label="Como a marca fala com ele" value={profile.audience.speaks_to_them_as} />
          </div>
          <h3 className="pt-2 text-sm font-medium">Pilares de mensagem</h3>
          <ListBlock items={profile.messaging_pillars} />
        </section>

        <section className="space-y-3 rounded-lg border bg-card p-3 shadow-sm">
          <h3 className="text-sm font-medium">Pode</h3>
          <ListBlock items={profile.guardrails.do} />
        </section>

        <section className="space-y-3 rounded-lg border bg-card p-3 shadow-sm">
          <h3 className="text-sm font-medium">Não pode</h3>
          <ListBlock items={profile.guardrails.dont} />
        </section>
      </div>

      <section className="space-y-2 rounded-lg border bg-card p-3 shadow-sm">
        <h3 className="text-sm font-medium">Exemplos de referência</h3>
        {profile.reference_examples.length === 0 ? (
          <p className="text-xs text-muted-foreground">—</p>
        ) : (
          <ul className="space-y-1.5">
            {profile.reference_examples.map((example) => (
              <li key={example} className="text-xs italic text-muted-foreground">
                “{example}”
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  )
}

function InfoRow({ label, value }: { label: string; value: string | null }) {
  return (
    <p>
      <span className="font-medium text-muted-foreground">{label}: </span>
      {value || '—'}
    </p>
  )
}

function ListBlock({ items }: { items: string[] }) {
  if (items.length === 0) return <p className="text-xs text-muted-foreground">—</p>
  return (
    <ul className="space-y-1 text-xs">
      {items.map((item) => (
        <li key={item} className="flex gap-1.5">
          <span className="text-muted-foreground">•</span>
          <span>{item}</span>
        </li>
      ))}
    </ul>
  )
}

function TagList({ items, tone }: { items: string[]; tone?: 'positive' | 'negative' }) {
  if (items.length === 0) return <p className="text-xs text-muted-foreground">—</p>
  const className =
    tone === 'positive'
      ? 'border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-900 dark:bg-emerald-950 dark:text-emerald-400'
      : tone === 'negative'
        ? 'border-rose-200 bg-rose-50 text-rose-700 dark:border-rose-900 dark:bg-rose-950 dark:text-rose-400'
        : undefined
  return (
    <div className="flex flex-wrap gap-1.5">
      {items.map((item) => (
        <Badge key={item} variant="outline" className={className}>
          {item}
        </Badge>
      ))}
    </div>
  )
}

function BrandArchetypeProfileSheet({
  open,
  company,
  profile,
  onClose,
}: {
  open: boolean
  company: Company | null
  profile: BrandArchetypeProfile | null
  onClose: () => void
}) {
  const createProfile = useCreateBrandArchetypeProfile()
  const updateProfile = useUpdateBrandArchetypeProfile()

  const [primaryArchetype, setPrimaryArchetype] = useState<BrandArchetype | ''>('')
  const [secondaryArchetype, setSecondaryArchetype] = useState<string>(NO_SECONDARY_ARCHETYPE)
  const [coreDesire, setCoreDesire] = useState('')
  const [fear, setFear] = useState('')
  const [strategy, setStrategy] = useState('')
  const [tone, setTone] = useState('')
  const [sentenceStyle, setSentenceStyle] = useState('')
  const [vocabularyPrefer, setVocabularyPrefer] = useState('')
  const [vocabularyAvoid, setVocabularyAvoid] = useState('')
  const [audienceWho, setAudienceWho] = useState('')
  const [audienceSpeaksAs, setAudienceSpeaksAs] = useState('')
  const [messagingPillars, setMessagingPillars] = useState('')
  const [guardrailsDo, setGuardrailsDo] = useState('')
  const [guardrailsDont, setGuardrailsDont] = useState('')
  const [referenceExamples, setReferenceExamples] = useState('')

  useEffect(() => {
    if (!open) return
    setPrimaryArchetype(profile?.primary_archetype ?? '')
    setSecondaryArchetype(profile?.secondary_archetype ?? NO_SECONDARY_ARCHETYPE)
    setCoreDesire(profile?.core_desire ?? '')
    setFear(profile?.fear ?? '')
    setStrategy(profile?.strategy ?? '')
    setTone(arrayToLines(profile?.voice.tone))
    setSentenceStyle(profile?.voice.sentence_style ?? '')
    setVocabularyPrefer(arrayToLines(profile?.voice.vocabulary_prefer))
    setVocabularyAvoid(arrayToLines(profile?.voice.vocabulary_avoid))
    setAudienceWho(profile?.audience.who ?? '')
    setAudienceSpeaksAs(profile?.audience.speaks_to_them_as ?? '')
    setMessagingPillars(arrayToLines(profile?.messaging_pillars))
    setGuardrailsDo(arrayToLines(profile?.guardrails.do))
    setGuardrailsDont(arrayToLines(profile?.guardrails.dont))
    setReferenceExamples(arrayToLines(profile?.reference_examples))
  }, [open, profile])

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!primaryArchetype) {
      toast.error('Selecione o arquétipo primário')
      return
    }

    const payload: Omit<BrandArchetypeProfileCreateInput, 'company_id'> = {
      primary_archetype: primaryArchetype,
      secondary_archetype:
        secondaryArchetype === NO_SECONDARY_ARCHETYPE
          ? null
          : (secondaryArchetype as BrandArchetype),
      core_desire: coreDesire || null,
      fear: fear || null,
      strategy: strategy || null,
      voice: {
        tone: linesToArray(tone),
        sentence_style: sentenceStyle || null,
        vocabulary_prefer: linesToArray(vocabularyPrefer),
        vocabulary_avoid: linesToArray(vocabularyAvoid),
      },
      audience: {
        who: audienceWho || null,
        speaks_to_them_as: audienceSpeaksAs || null,
      },
      messaging_pillars: linesToArray(messagingPillars),
      guardrails: {
        do: linesToArray(guardrailsDo),
        dont: linesToArray(guardrailsDont),
      },
      reference_examples: linesToArray(referenceExamples),
    }

    if (profile) {
      updateProfile.mutate({ id: profile.id, data: payload }, { onSuccess: onClose })
    } else {
      if (!company) return
      createProfile.mutate({ ...payload, company_id: company.id }, { onSuccess: onClose })
    }
  }

  const isPending = createProfile.isPending || updateProfile.isPending

  return (
    <Sheet open={open} onOpenChange={(nextOpen) => !nextOpen && onClose()}>
      <SheetContent className="overflow-y-auto data-[side=right]:w-full data-[side=right]:sm:max-w-none data-[side=right]:lg:w-[50vw]">
        <SheetHeader>
          <SheetTitle>{profile ? 'Editar arquétipo de marca' : 'Criar arquétipo de marca'}</SheetTitle>
          <SheetDescription>
            Preenchimento manual por enquanto — ver docs/arquetipos-de-marca.md para o framework e o
            questionário de diagnóstico usados como referência.
          </SheetDescription>
        </SheetHeader>

        <form className="space-y-4 px-4 pb-6" onSubmit={onSubmit}>
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label>Arquétipo primário</Label>
              <Select
                value={primaryArchetype || undefined}
                onValueChange={(value) => setPrimaryArchetype(value as BrandArchetype)}
              >
                <SelectTrigger className="w-full">
                  <SelectValue placeholder="Selecione..." />
                </SelectTrigger>
                <SelectContent>
                  {BRAND_ARCHETYPES.map((archetype) => (
                    <SelectItem key={archetype.value} value={archetype.value}>
                      {archetype.label} — {archetype.hint}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Arquétipo secundário</Label>
              <Select value={secondaryArchetype} onValueChange={setSecondaryArchetype}>
                <SelectTrigger className="w-full">
                  <SelectValue placeholder="Nenhum" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value={NO_SECONDARY_ARCHETYPE}>Nenhum</SelectItem>
                  {BRAND_ARCHETYPES.map((archetype) => (
                    <SelectItem key={archetype.value} value={archetype.value}>
                      {archetype.label} — {archetype.hint}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="grid gap-4 sm:grid-cols-3">
            <div className="space-y-2">
              <Label htmlFor="ba-core-desire">Desejo central</Label>
              <Input
                id="ba-core-desire"
                value={coreDesire}
                onChange={(event) => setCoreDesire(event.target.value)}
                placeholder="ex: ajudar o cliente a decidir bem"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="ba-fear">Medo</Label>
              <Input
                id="ba-fear"
                value={fear}
                onChange={(event) => setFear(event.target.value)}
                placeholder="ex: parecer genérico"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="ba-strategy">Estratégia</Label>
              <Input
                id="ba-strategy"
                value={strategy}
                onChange={(event) => setStrategy(event.target.value)}
                placeholder="ex: educar antes de vender"
              />
            </div>
          </div>

          <section className="space-y-3 rounded-lg border bg-card p-3 shadow-sm">
            <h3 className="text-sm font-medium">Voz</h3>
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="ba-tone">Tom (um por linha)</Label>
                <Textarea
                  id="ba-tone"
                  value={tone}
                  onChange={(event) => setTone(event.target.value)}
                  placeholder={'direto\nconfiante\nacolhedor'}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="ba-sentence-style">Estilo de frase</Label>
                <Input
                  id="ba-sentence-style"
                  value={sentenceStyle}
                  onChange={(event) => setSentenceStyle(event.target.value)}
                  placeholder="frases curtas, sem jargão técnico"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="ba-vocab-prefer">Vocabulário preferido (um por linha)</Label>
                <Textarea
                  id="ba-vocab-prefer"
                  value={vocabularyPrefer}
                  onChange={(event) => setVocabularyPrefer(event.target.value)}
                  placeholder={'conforto\ncaimento perfeito'}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="ba-vocab-avoid">Vocabulário a evitar (um por linha)</Label>
                <Textarea
                  id="ba-vocab-avoid"
                  value={vocabularyAvoid}
                  onChange={(event) => setVocabularyAvoid(event.target.value)}
                  placeholder={'imperdível\ncorre que acaba'}
                />
              </div>
            </div>
          </section>

          <section className="space-y-3 rounded-lg border bg-card p-3 shadow-sm">
            <h3 className="text-sm font-medium">Público</h3>
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="ba-audience-who">Quem é</Label>
                <Input
                  id="ba-audience-who"
                  value={audienceWho}
                  onChange={(event) => setAudienceWho(event.target.value)}
                  placeholder="mulheres 25-40, classe B"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="ba-audience-speaks-as">Como a marca fala com ele</Label>
                <Input
                  id="ba-audience-speaks-as"
                  value={audienceSpeaksAs}
                  onChange={(event) => setAudienceSpeaksAs(event.target.value)}
                  placeholder="como amiga que entende de moda"
                />
              </div>
            </div>
          </section>

          <div className="space-y-2">
            <Label htmlFor="ba-pillars">Pilares de mensagem (um por linha)</Label>
            <Textarea
              id="ba-pillars"
              value={messagingPillars}
              onChange={(event) => setMessagingPillars(event.target.value)}
              placeholder={'qualidade que dura\ncaimento para o corpo real'}
            />
          </div>

          <div className="grid gap-3 sm:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="ba-guardrails-do">Pode (um por linha)</Label>
              <Textarea
                id="ba-guardrails-do"
                value={guardrailsDo}
                onChange={(event) => setGuardrailsDo(event.target.value)}
                placeholder={'citar benefício concreto'}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="ba-guardrails-dont">Não pode (um por linha)</Label>
              <Textarea
                id="ba-guardrails-dont"
                value={guardrailsDont}
                onChange={(event) => setGuardrailsDont(event.target.value)}
                placeholder={'prometer desconto que não existe'}
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="ba-examples">Exemplos de referência (um por linha)</Label>
            <Textarea
              id="ba-examples"
              value={referenceExamples}
              onChange={(event) => setReferenceExamples(event.target.value)}
              placeholder="Não é sobre seguir tendência. É sobre vestir o que combina com você."
            />
          </div>

          <div className="sticky bottom-0 -mx-4 flex justify-end gap-2 border-t bg-popover/95 p-4 backdrop-blur">
            <Button type="button" variant="outline" onClick={onClose}>
              Cancelar
            </Button>
            <Button disabled={isPending}>
              {isPending ? (
                <Loader2 className="size-4 animate-spin" />
              ) : (
                <CheckCircle2 className="size-4" />
              )}
              Salvar
            </Button>
          </div>
        </form>
      </SheetContent>
    </Sheet>
  )
}
