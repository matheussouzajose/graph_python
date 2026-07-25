import { useEffect, useMemo, useState } from 'react'
import type { FormEvent, ReactNode } from 'react'
import {
  Building2,
  CheckCircle2,
  Database,
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
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { EmptyState } from '@/components/shared/EmptyState'
import { PageHeader } from '@/components/shared/PageHeader'
import { RelativeTime } from '@/components/shared/RelativeTime'
import { SectionCard } from '@/components/shared/SectionCard'
import {
  useCompanies,
  useDeleteIntegration,
  useIntegrations,
  useUpdateIntegration,
} from '@/hooks/use-catalog'
import {
  useGraphSyncAction,
  useRunAlgorithmsAction,
  useRunEmbeddingsAction,
  useSyncIntegrationAction,
} from '@/hooks/use-actions'
import type { Integration } from '@/types/api'

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
          <IntegrationsSettings integrations={integrations.data} loading={integrations.isLoading} />
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

function IntegrationsSettings({
  integrations,
  loading,
}: {
  integrations: Integration[] | undefined
  loading?: boolean
}) {
  const [editing, setEditing] = useState<Integration | null>(null)
  const [deleting, setDeleting] = useState<Integration | null>(null)
  const deleteIntegration = useDeleteIntegration()
  const syncIntegration = useSyncIntegrationAction()
  const graphSyncAction = useGraphSyncAction()
  const algorithmsAction = useRunAlgorithmsAction()
  const embeddingsAction = useRunEmbeddingsAction()

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
      >
          {loading ? (
            <div className="h-48 animate-pulse rounded-lg bg-muted" />
          ) : !integrations || integrations.length === 0 ? (
            <EmptyState title="Nenhuma integração cadastrada" />
          ) : (
            <div className="grid gap-3">
              {integrations.map((integration) => (
                <div
                  key={integration.id}
                  className="grid gap-3 rounded-lg border bg-card p-4 shadow-sm lg:grid-cols-[1fr_auto]"
                >
                  <div className="min-w-0 space-y-2">
                    <div className="flex flex-wrap items-center gap-2">
                      <h3 className="truncate text-sm font-semibold">{integration.name}</h3>
                      <Badge variant="outline">{integration.provider}</Badge>
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
                    </div>
                    <p className="truncate font-mono text-xs text-muted-foreground">
                      {integration.base_url}
                    </p>
                    <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
                      <span>ID {integration.id}</span>
                      <span>
                        Atualizada <RelativeTime value={integration.updated_at} />
                      </span>
                    </div>
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
              ))}
            </div>
          )}
      </SectionCard>

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
  const [isActive, setIsActive] = useState(true)

  useEffect(() => {
    if (!integration) return
    setName(integration.name)
    setBaseUrl(integration.base_url)
    setConfigs(objectToRows(integration.configs))
    setParams(objectToRows(integration.params))
    setIsActive(integration.is_active)
  }, [integration])

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!integration) return

    try {
      const parsedConfigs = rowsToObject(configs, 'Configs')
      const parsedParams = rowsToObject(params, 'Params')
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
