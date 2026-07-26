import { useEffect, useMemo, useRef, useState } from 'react'
import type { FormEvent, ReactNode } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import {
  ArrowLeft,
  Bot,
  Check,
  CheckCircle2,
  ChevronDown,
  Clock,
  Copy,
  Globe,
  ImageIcon,
  ImageOff,
  Info,
  Loader2,
  Pencil,
  Play,
  Plus,
  Search,
  Sparkles,
  Square,
  Trash2,
  Video,
  Wand2,
  X,
  XCircle,
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
import { ScrollArea } from '@/components/ui/scroll-area'
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
import { Textarea } from '@/components/ui/textarea'
import { EmptyState } from '@/components/shared/EmptyState'
import { RelativeTime } from '@/components/shared/RelativeTime'
import {
  agentKeys,
  useAgentRuns,
  useAgents,
  useApplyAgentRun,
  useCreateAgent,
  useDeleteAgent,
  usePollAgentRun,
  useRunAgentOnce,
  useUpdateAgent,
  useUpdateAgentRunOutput,
} from '@/hooks/use-agents'
import { useAgentRunStream } from '@/hooks/use-agent-run-stream'
import { useProducts } from '@/hooks/use-products'
import { useAuthUser } from '@/lib/auth-kit-core'
import { AGENT_OUTPUT_ACTIONS, AGENT_OUTPUT_ACTION_APPLY_LABEL } from '@/lib/agent-actions'
import { fetchAgentRunVideo } from '@/lib/api'
import { productImages } from '@/lib/product-images'
import { cn } from '@/lib/utils'
import type {
  Agent,
  AgentCreateInput,
  AgentKind,
  AgentOutputAction,
  AgentResponseFormat,
  AgentRun,
  AgentVideoProvider,
  AuthUser,
  VideoSeconds,
  VideoSize,
} from '@/types/api'

const AGENTS_PER_PAGE = 9

const VIDEO_SIZE_OPTIONS: { value: VideoSize; label: string }[] = [
  { value: '720x1280', label: 'Retrato pequeno (720x1280)' },
  { value: '1280x720', label: 'Paisagem pequena (1280x720)' },
  { value: '1024x1792', label: 'Retrato grande (1024x1792)' },
  { value: '1792x1024', label: 'Paisagem grande (1792x1024)' },
]

const VIDEO_SECONDS_OPTIONS: VideoSeconds[] = ['4', '8', '12']
type AgentScopeFilter = 'all' | 'mine' | 'global'
type AgentKindFilter = 'all' | AgentKind
type AgentStatusFilter = 'all' | 'active' | 'inactive'

export function AgentsPage() {
  const authUser = useAuthUser<AuthUser>()
  const agents = useAgents()

  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [editing, setEditing] = useState<Agent | 'new' | null>(null)
  const [deleting, setDeleting] = useState<Agent | null>(null)

  const isAdmin = authUser?.role === 'admin'
  const myCompanyId = authUser?.company_id

  const sortedAgents = useMemo(() => {
    if (!agents.data) return []
    return [...agents.data].sort((a, b) => {
      const aMine = a.company_id === myCompanyId ? 0 : 1
      const bMine = b.company_id === myCompanyId ? 0 : 1
      if (aMine !== bMine) return aMine - bMine
      return a.name.localeCompare(b.name)
    })
  }, [agents.data, myCompanyId])

  const selectedAgent = sortedAgents.find((agent) => agent.id === selectedId) ?? null
  const ownedCount = sortedAgents.filter((agent) => agent.company_id === myCompanyId).length
  const globalCount = sortedAgents.filter((agent) => agent.is_global).length
  const activeCount = sortedAgents.filter((agent) => agent.is_active).length

  return (
    <div className="flex min-h-[calc(100vh-7rem)] flex-col gap-4">
      <section className="dark-panel relative overflow-hidden rounded-3xl p-5 sm:p-6">
        <div className="surface-glow absolute right-8 top-0 h-44 w-44 rounded-full bg-violet-400/18 blur-3xl" />
        <div className="absolute -bottom-20 left-1/4 h-44 w-44 rounded-full bg-teal-300/12 blur-3xl" />
        <div className="relative grid gap-5 lg:grid-cols-[1fr_420px] lg:items-center">
          <div>
            <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/8 px-3 py-1.5 text-xs text-violet-100">
              <Wand2 className="size-3.5" />
              Workbench de IA
            </div>
            <h2 className="mt-4 max-w-2xl text-3xl font-semibold tracking-normal">
              Execute agentes como ferramentas de operação, não como formulários soltos.
            </h2>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-white/55">
              Biblioteca, execução, revisão e aplicação de saída estruturada ficam no mesmo fluxo
              para acelerar tarefas comerciais.
            </p>
          </div>
          <div className="grid gap-3 sm:grid-cols-3">
            <AgentSignal label="Ativos" value={activeCount} />
            <AgentSignal label="Seus" value={ownedCount} />
            <AgentSignal label="Globais" value={globalCount} />
            <Button
              className="h-auto rounded-2xl bg-white text-slate-950 shadow-lg shadow-black/20 hover:bg-white/90 sm:col-span-3"
              onClick={() => setEditing('new')}
            >
              <Plus className="size-4" />
              Criar agente
            </Button>
          </div>
        </div>
      </section>

      {selectedAgent ? (
        <div className="flex min-h-[calc(100vh-12rem)] flex-col overflow-hidden rounded-3xl border bg-card/86 shadow-sm shadow-slate-950/[0.04] backdrop-blur">
          <AgentWorkspace
            agent={selectedAgent}
            mine={selectedAgent.company_id === myCompanyId}
            onBack={() => setSelectedId(null)}
            onEdit={() => setEditing(selectedAgent)}
            onDelete={() => setDeleting(selectedAgent)}
          />
        </div>
      ) : (
        <AgentLibrary
          agents={sortedAgents}
          loading={agents.isLoading}
          myCompanyId={myCompanyId}
          onSelect={(agent) => setSelectedId(agent.id)}
          onCreate={() => setEditing('new')}
        />
      )}

      <AgentEditSheet
        open={editing !== null}
        agent={editing === 'new' ? null : editing}
        companyId={myCompanyId}
        canGoGlobal={isAdmin}
        onClose={() => setEditing(null)}
        onCreated={(agent) => setSelectedId(agent.id)}
      />

      <Dialog open={Boolean(deleting)} onOpenChange={(open) => !open && setDeleting(null)}>
        <DialogContent>
          <DeleteAgentDialogContent agent={deleting} onClose={() => setDeleting(null)} />
        </DialogContent>
      </Dialog>
    </div>
  )
}

function AgentSignal({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-2xl border border-white/10 bg-white/[0.075] p-3">
      <div className="flex items-center justify-between gap-3">
        <p className="text-xs text-white/45">{label}</p>
        <Bot className="size-4 text-violet-200" />
      </div>
      <p className="mt-1 truncate text-lg font-semibold">{value}</p>
    </div>
  )
}

function AgentLibrary({
  agents,
  loading,
  myCompanyId,
  onSelect,
  onCreate,
}: {
  agents: Agent[]
  loading: boolean
  myCompanyId: string | undefined
  onSelect: (agent: Agent) => void
  onCreate: () => void
}) {
  const [query, setQuery] = useState('')
  const [page, setPage] = useState(1)
  const [scope, setScope] = useState<AgentScopeFilter>('all')
  const [kind, setKind] = useState<AgentKindFilter>('all')
  const [status, setStatus] = useState<AgentStatusFilter>('all')

  const filteredAgents = useMemo(() => {
    const normalized = query.trim().toLocaleLowerCase()
    return agents.filter((agent) => {
      if (scope === 'mine' && agent.company_id !== myCompanyId) return false
      if (scope === 'global' && !agent.is_global) return false
      if (kind !== 'all' && agent.kind !== kind) return false
      if (status === 'active' && !agent.is_active) return false
      if (status === 'inactive' && agent.is_active) return false
      if (!normalized) return true
      return [agent.name, agent.description, agent.usage_instructions, agent.system_prompt]
        .filter(Boolean)
        .some((value) => value?.toLocaleLowerCase().includes(normalized))
    })
  }, [agents, kind, myCompanyId, query, scope, status])

  const totalPages = Math.max(1, Math.ceil(filteredAgents.length / AGENTS_PER_PAGE))
  const currentPage = Math.min(page, totalPages)
  const pageAgents = filteredAgents.slice(
    (currentPage - 1) * AGENTS_PER_PAGE,
    currentPage * AGENTS_PER_PAGE,
  )

  useEffect(() => {
    setPage(1)
  }, [query, agents.length, scope, kind, status])

  const ownedCount = agents.filter((agent) => agent.company_id === myCompanyId).length
  const globalCount = agents.filter((agent) => agent.is_global).length
  const activeCount = agents.filter((agent) => agent.is_active).length

  if (loading) {
    return (
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {Array.from({ length: 6 }).map((_, index) => (
          <div key={index} className="h-56 animate-pulse rounded-3xl border bg-muted/70" />
        ))}
      </div>
    )
  }

  if (agents.length === 0) {
    return (
      <div className="flex min-h-[24rem] items-center justify-center rounded-xl border bg-card p-6 shadow-sm">
        <EmptyState
          icon={Bot}
          title="Nenhum agente ainda"
          description="Crie o primeiro agente definindo instruções e ele aparecerá nesta biblioteca."
          action={
            <Button onClick={onCreate}>
              <Plus className="size-4" />
              Criar agente
            </Button>
          }
        />
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="glass-panel rounded-3xl p-3">
      <div className="grid gap-3 lg:grid-cols-[1fr_auto] lg:items-center">
        <div className="relative">
          <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Buscar por nome, descrição ou instrução"
            className="h-11 rounded-2xl bg-card pl-9"
          />
        </div>
        <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
          <Badge variant="outline">{agents.length} agentes</Badge>
          <Badge variant="outline">{ownedCount} seus</Badge>
          <Badge variant="outline">{globalCount} globais</Badge>
          <Badge variant="outline">{activeCount} ativos</Badge>
        </div>
      </div>
      <div className="mt-3 flex flex-wrap gap-2 border-t border-border/60 pt-3">
        <SegmentButton active={scope === 'all'} onClick={() => setScope('all')}>Todos</SegmentButton>
        <SegmentButton active={scope === 'mine'} onClick={() => setScope('mine')}>Seus</SegmentButton>
        <SegmentButton active={scope === 'global'} onClick={() => setScope('global')}>Globais</SegmentButton>
        <span className="mx-1 hidden h-7 w-px bg-border sm:block" />
        <SegmentButton active={kind === 'all'} onClick={() => setKind('all')}>Todos os tipos</SegmentButton>
        <SegmentButton active={kind === 'chat'} onClick={() => setKind('chat')}>Chat</SegmentButton>
        <SegmentButton active={kind === 'image_to_video'} onClick={() => setKind('image_to_video')}>Vídeo</SegmentButton>
        <span className="mx-1 hidden h-7 w-px bg-border sm:block" />
        <SegmentButton active={status === 'all'} onClick={() => setStatus('all')}>Qualquer status</SegmentButton>
        <SegmentButton active={status === 'active'} onClick={() => setStatus('active')}>Ativos</SegmentButton>
        <SegmentButton active={status === 'inactive'} onClick={() => setStatus('inactive')}>Inativos</SegmentButton>
      </div>
      </div>

      {filteredAgents.length === 0 ? (
        <div className="flex min-h-[18rem] items-center justify-center rounded-xl border bg-card p-6 shadow-sm">
          <EmptyState
            icon={Search}
            title="Nenhum agente encontrado"
            description="Ajuste a busca para ver outros agentes disponíveis."
            action={
              <Button
                variant="outline"
                onClick={() => {
                  setQuery('')
                  setScope('all')
                  setKind('all')
                  setStatus('all')
                }}
              >
                Limpar filtros
              </Button>
            }
          />
        </div>
      ) : (
        <>
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {pageAgents.map((agent) => (
              <AgentCard
                key={agent.id}
                agent={agent}
                mine={agent.company_id === myCompanyId}
                onClick={() => onSelect(agent)}
              />
            ))}
          </div>

          <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border bg-card/86 px-3 py-2.5 shadow-sm shadow-slate-950/[0.03]">
            <p className="text-sm text-muted-foreground">
              Página {currentPage} de {totalPages} · {filteredAgents.length} resultado
              {filteredAgents.length === 1 ? '' : 's'}
            </p>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                disabled={currentPage === 1}
                onClick={() => setPage((value) => Math.max(1, value - 1))}
              >
                Anterior
              </Button>
              <Button
                variant="outline"
                size="sm"
                disabled={currentPage === totalPages}
                onClick={() => setPage((value) => Math.min(totalPages, value + 1))}
              >
                Próxima
              </Button>
            </div>
          </div>
        </>
      )}

      <div className="flex justify-end sm:hidden">
        <Button onClick={onCreate}>
          <Plus className="size-4" />
          Criar agente
        </Button>
      </div>
    </div>
  )
}

function SegmentButton({
  active,
  onClick,
  children,
}: {
  active: boolean
  onClick: () => void
  children: ReactNode
}) {
  return (
    <Button
      type="button"
      variant={active ? 'secondary' : 'ghost'}
      size="sm"
      className="rounded-xl"
      onClick={onClick}
    >
      {children}
    </Button>
  )
}

function AgentCard({
  agent,
  mine,
  onClick,
}: {
  agent: Agent
  mine: boolean
  onClick: () => void
}) {
  const outputLabel =
    AGENT_OUTPUT_ACTIONS.find((action) => action.value === agent.output_action)?.label ??
    'Resultado configurado'

  return (
    <button
      type="button"
      onClick={onClick}
      className="group relative flex min-h-60 w-full flex-col overflow-hidden rounded-3xl border bg-card/88 p-4 text-left shadow-sm shadow-slate-950/[0.035] transition hover:-translate-y-1 hover:border-primary/35 hover:shadow-xl hover:shadow-slate-950/[0.08] focus-visible:border-primary focus-visible:outline-none focus-visible:ring-3 focus-visible:ring-ring/30"
    >
      <div className="surface-glow pointer-events-none absolute -right-12 -top-12 h-28 w-28 rounded-full bg-primary/10 blur-2xl" />
      <div className="relative flex items-start gap-3">
        <div
          className={cn(
            'flex size-12 shrink-0 items-center justify-center rounded-2xl text-white shadow-lg transition group-hover:scale-105',
            agent.kind === 'image_to_video' ? 'bg-violet-500 shadow-violet-500/20' : 'bg-primary shadow-primary/20',
          )}
        >
          {agent.kind === 'image_to_video' ? <Video className="size-5" /> : <Bot className="size-5" />}
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-1.5">
            <h3 className="min-w-0 text-base font-semibold leading-6 tracking-normal">
              {agent.name}
            </h3>
            {agent.is_global ? (
              <Badge
                variant="outline"
                className="border-blue-200 bg-blue-50 text-blue-700 dark:border-blue-900 dark:bg-blue-950 dark:text-blue-400"
              >
                <Globe className="size-3" />
                Global
              </Badge>
            ) : null}
          </div>
          <p className="mt-1 line-clamp-2 text-sm leading-5 text-muted-foreground">
            {agent.description || 'Agente sem descrição curta.'}
          </p>
        </div>
      </div>

      <div className="relative mt-4 flex flex-wrap gap-2">
        <Badge
          variant={agent.is_active ? 'secondary' : 'outline'}
          className={agent.is_active ? 'bg-emerald-50 text-emerald-700 ring-1 ring-emerald-200' : ''}
        >
          {agent.is_active ? 'Ativo' : 'Inativo'}
        </Badge>
        <Badge variant="outline">{mine ? 'Seu agente' : 'Compartilhado'}</Badge>
        {agent.kind === 'image_to_video' ? (
          <Badge variant="outline">
            <Video className="size-3" />
            Vídeo
          </Badge>
        ) : null}
        {agent.uses_brand_archetype ? <Badge variant="outline">Usa arquétipo</Badge> : null}
      </div>

      <div className="relative mt-4 grid gap-2 rounded-2xl border bg-muted/25 p-3">
        <div className="flex items-center justify-between gap-3 text-xs">
          <span className="text-muted-foreground">Modelo</span>
          <span className="truncate font-medium">{agent.model || 'Padrão'}</span>
        </div>
        <div className="flex items-center justify-between gap-3 text-xs">
          <span className="text-muted-foreground">Formato</span>
          <span className="font-medium">
            {agent.kind === 'image_to_video'
              ? `${agent.video_provider === 'openrouter' ? 'OpenRouter' : 'Sora'}`
              : agent.response_format === 'json'
                ? 'JSON'
                : 'Texto'}
          </span>
        </div>
        <div className="flex items-center justify-between gap-3 text-xs">
          <span className="text-muted-foreground">Atualizado</span>
          <span className="font-medium"><RelativeTime value={agent.updated_at} /></span>
        </div>
      </div>

      <div className="relative mt-auto pt-4">
        <div className="rounded-2xl border bg-card px-3 py-2 shadow-sm">
          <p className="line-clamp-1 text-xs font-medium text-foreground/80">{outputLabel}</p>
          <p className="mt-0.5 text-xs text-muted-foreground">
            {agent.response_format === 'json' ? 'Resposta estruturada' : 'Resposta em texto'}
          </p>
        </div>
        <div className="mt-3 flex items-center justify-between text-xs font-medium text-primary">
          <span>Abrir workspace</span>
          <Play className="size-3.5 transition group-hover:translate-x-1" />
        </div>
      </div>
    </button>
  )
}

function DeleteAgentDialogContent({
  agent,
  onClose,
}: {
  agent: Agent | null
  onClose: () => void
}) {
  const deleteAgent = useDeleteAgent()
  return (
    <>
      <DialogHeader>
        <DialogTitle>Excluir agente</DialogTitle>
        <DialogDescription>
          Remove o agente e não afeta execuções já feitas por outras empresas, se ele era global.
        </DialogDescription>
      </DialogHeader>
      <p className="text-sm">
        Confirma a exclusão de <strong>{agent?.name}</strong>?
      </p>
      <DialogFooter>
        <Button variant="outline" onClick={onClose}>
          Cancelar
        </Button>
        <Button
          variant="destructive"
          disabled={deleteAgent.isPending}
          onClick={() => {
            if (!agent) return
            deleteAgent.mutate(agent.id, { onSuccess: onClose })
          }}
        >
          {deleteAgent.isPending ? (
            <Loader2 className="size-4 animate-spin" />
          ) : (
            <Trash2 className="size-4" />
          )}
          Excluir
        </Button>
      </DialogFooter>
    </>
  )
}

function AgentWorkspace({
  agent,
  mine,
  onBack,
  onEdit,
  onDelete,
}: {
  agent: Agent
  mine: boolean
  onBack: () => void
  onEdit: () => void
  onDelete: () => void
}) {
  const isVideoKind = agent.kind === 'image_to_video'
  const queryClient = useQueryClient()
  const runs = useAgentRuns(agent.id)
  const stream = useAgentRunStream()
  const applyRun = useApplyAgentRun()
  const updateOutput = useUpdateAgentRunOutput()
  const runVideo = useRunAgentOnce()

  const [message, setMessage] = useState('')
  const [showContext, setShowContext] = useState(false)
  const [contextRows, setContextRows] = useState<{ id: string; key: string; value: string }[]>([])
  const [selectedImageUrls, setSelectedImageUrls] = useState<string[]>([])
  const [viewedRun, setViewedRun] = useState<AgentRun | null>(null)
  const [editingText, setEditingText] = useState<string | null>(null)
  const bottomRef = useRef<HTMLDivElement | null>(null)

  const videoRunUnsettled = Boolean(
    viewedRun && (viewedRun.status === 'running' || viewedRun.status === 'pending'),
  )
  const poll = usePollAgentRun(isVideoKind ? (viewedRun?.id ?? null) : null, videoRunUnsettled)

  useEffect(() => {
    if (poll.data) setViewedRun(poll.data)
  }, [poll.data])

  useEffect(() => {
    stream.reset()
    applyRun.reset()
    setMessage('')
    setContextRows([])
    setShowContext(false)
    setSelectedImageUrls([])
    setViewedRun(null)
    setEditingText(null)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [agent.id])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [stream.text, viewedRun])

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    if (isVideoKind) {
      if (selectedImageUrls.length === 0 || videoRunUnsettled) return
      const videoMessage = message.trim() || 'Gere um vídeo publicitário curto para este produto.'
      setViewedRun(null)
      applyRun.reset()
      runVideo.mutate(
        { id: agent.id, data: { message: videoMessage, image_urls: selectedImageUrls } },
        {
          onSuccess: (run) => {
            setViewedRun(run)
            setMessage('')
            queryClient.invalidateQueries({ queryKey: agentKeys.runs(agent.id) })
          },
        },
      )
      return
    }

    const trimmed = message.trim()
    if (!trimmed || stream.isStreaming) return

    const variables: Record<string, unknown> = {}
    for (const row of contextRows) {
      if (row.key.trim()) variables[row.key.trim()] = row.value
    }

    setViewedRun(null)
    setEditingText(null)
    applyRun.reset()
    setMessage('')
    stream.start(agent.id, trimmed, variables, () => {
      queryClient.invalidateQueries({ queryKey: agentKeys.runs(agent.id) })
      queryClient.invalidateQueries({ queryKey: agentKeys.runs(undefined) })
    })
  }

  const displayedRun = viewedRun ?? stream.run
  const displayedText = stream.isStreaming || (!displayedRun && stream.text) ? stream.text : displayedRun?.output?.text ?? ''
  const canApply =
    agent.output_action !== 'none' &&
    displayedRun?.status === 'completed' &&
    Boolean(displayedRun?.output?.data)

  return (
    <>
      <div className="dark-panel relative overflow-hidden border-b border-white/10 p-4 sm:p-5">
        <div className="surface-glow absolute right-8 top-0 h-36 w-36 rounded-full bg-violet-400/18 blur-3xl" />
        <div className="relative space-y-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="flex min-w-0 items-start gap-3">
            <Button
              variant="outline"
              size="icon"
              className="mt-1 shrink-0 border-white/10 bg-white/[0.08] text-white hover:bg-white/[0.14]"
              onClick={onBack}
            >
              <ArrowLeft className="size-4" />
            </Button>
            <div className="flex size-12 shrink-0 items-center justify-center rounded-2xl bg-white text-slate-950 shadow-lg shadow-black/20">
              {isVideoKind ? <Video className="size-5" /> : <Bot className="size-5" />}
            </div>
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <h2 className="text-xl font-semibold tracking-normal">{agent.name}</h2>
                {agent.is_global ? (
                  <Badge
                    variant="outline"
                    className="border-white/10 bg-white/[0.08] text-white"
                  >
                    <Globe className="size-3" />
                    Global
                  </Badge>
                ) : null}
                {!agent.is_active ? <Badge variant="outline">Inativo</Badge> : null}
              </div>
              {agent.description ? (
                <p className="mt-1 max-w-2xl text-sm leading-6 text-white/58">{agent.description}</p>
              ) : null}
            </div>
          </div>
          {mine ? (
            <div className="flex shrink-0 items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                className="border-white/10 bg-white/[0.08] text-white hover:bg-white/[0.14]"
                onClick={onEdit}
              >
                <Pencil className="size-4" />
                Editar
              </Button>
              <Button variant="destructive" size="sm" onClick={onDelete}>
                <Trash2 className="size-4" />
                Excluir
              </Button>
            </div>
          ) : null}
        </div>

        {agent.usage_instructions ? (
          <div className="flex gap-2.5 rounded-2xl border border-white/10 bg-white/[0.075] p-3 text-sm">
            <div className="mt-0.5 flex size-6 shrink-0 items-center justify-center rounded-full bg-white/10 text-teal-200">
              <Info className="size-3" />
            </div>
            <p className="whitespace-pre-wrap leading-6 text-white/72">
              {agent.usage_instructions}
            </p>
          </div>
        ) : null}
        </div>
      </div>

      <ScrollArea className="min-h-0 flex-1">
        <div className="grid w-full gap-4 px-4 py-5 xl:grid-cols-[minmax(0,1fr)_340px] xl:px-8">
          <div className="min-w-0 space-y-4">
          {!agent.is_active ? (
            <EmptyState
              icon={Bot}
              title="Agente inativo"
              description='Ative este agente em "Editar" para liberar execuções.'
              action={
                mine ? (
                  <Button variant="outline" onClick={onEdit}>
                    <Pencil className="size-4" />
                    Editar agente
                  </Button>
                ) : null
              }
            />
          ) : (
            <form
              onSubmit={onSubmit}
              className="space-y-2.5 rounded-3xl border bg-card/88 p-3 shadow-sm shadow-slate-950/[0.035] transition focus-within:border-primary/40 focus-within:shadow-lg"
            >
              {isVideoKind ? (
                <div className="space-y-2.5">
                  <CatalogImagePicker
                    value={selectedImageUrls}
                    onChange={setSelectedImageUrls}
                    maxImages={agent.video_provider === 'openai' ? 1 : undefined}
                  />
                  <Textarea
                    value={message}
                    onChange={(event) => setMessage(event.target.value)}
                    placeholder="Instruções extras para este vídeo (opcional)"
                    rows={2}
                    className="resize-none border-0 bg-transparent shadow-none focus-visible:ring-0"
                  />
                </div>
              ) : (
                <Textarea
                  value={message}
                  onChange={(event) => setMessage(event.target.value)}
                  onKeyDown={(event) => {
                    if (event.key === 'Enter' && !event.shiftKey) {
                      event.preventDefault()
                      event.currentTarget.form?.requestSubmit()
                    }
                  }}
                  placeholder="O que você quer pedir a este agente?"
                  rows={3}
                  className="resize-none border-0 bg-transparent shadow-none focus-visible:ring-0"
                />
              )}

              {!isVideoKind && showContext ? (
                <ExtraContextEditor rows={contextRows} onChange={setContextRows} />
              ) : null}

              <div className="flex items-center justify-between gap-2 border-t pt-2.5">
                {isVideoKind ? (
                  <span className="text-xs text-muted-foreground">
                    A geração leva alguns minutos.
                  </span>
                ) : (
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    className="text-xs text-muted-foreground"
                    onClick={() => setShowContext((open) => !open)}
                  >
                    {showContext ? 'Ocultar contexto extra' : '+ Adicionar contexto extra'}
                  </Button>
                )}
                <div className="flex items-center gap-3">
                  {isVideoKind ? (
                    <Button
                      type="submit"
                      disabled={
                        selectedImageUrls.length === 0 || runVideo.isPending || videoRunUnsettled
                      }
                    >
                      {runVideo.isPending || videoRunUnsettled ? (
                        <Loader2 className="size-4 animate-spin" />
                      ) : (
                        <Video className="size-4" />
                      )}
                      Gerar vídeo
                    </Button>
                  ) : (
                    <>
                      <span className="hidden text-xs text-muted-foreground sm:inline">
                        Enter para executar · Shift+Enter para nova linha
                      </span>
                      {stream.isStreaming ? (
                        <Button type="button" variant="outline" onClick={stream.stop}>
                          <Square className="size-4" />
                          Parar
                        </Button>
                      ) : (
                        <Button type="submit" disabled={!message.trim()}>
                          <Play className="size-4" />
                          Executar
                        </Button>
                      )}
                    </>
                  )}
                </div>
              </div>
            </form>
          )}

          {stream.error || (displayedRun?.status === 'failed' && displayedRun.error) ? (
            <p className="text-sm text-destructive">
              {stream.error || displayedRun?.error}
            </p>
          ) : null}

          {displayedText || stream.isStreaming || (isVideoKind && displayedRun) ? (
            <ResultCard
              agentName={agent.name}
              isVideoKind={isVideoKind}
              text={displayedText}
              isStreaming={stream.isStreaming}
              run={displayedRun}
              editingText={editingText}
              onStartEdit={() => setEditingText(displayedText)}
              onCancelEdit={() => setEditingText(null)}
              onChangeEdit={setEditingText}
              onSaveEdit={() => {
                if (!displayedRun || editingText === null) return
                updateOutput.mutate(
                  { id: displayedRun.id, text: editingText },
                  {
                    onSuccess: (run) => {
                      setViewedRun(run)
                      setEditingText(null)
                    },
                  },
                )
              }}
              savingEdit={updateOutput.isPending}
              canApply={canApply}
              applyLabel={
                AGENT_OUTPUT_ACTION_APPLY_LABEL[agent.output_action] ?? 'Aplicar resultado'
              }
              onApply={() => displayedRun && applyRun.mutate(displayedRun.id)}
              applying={applyRun.isPending}
              applied={applyRun.isSuccess}
            />
          ) : null}

          <div ref={bottomRef} />
          </div>

          <aside className="min-w-0 rounded-3xl border bg-card/70 p-3 shadow-sm shadow-slate-950/[0.035] xl:sticky xl:top-24 xl:self-start">
          <RunHistory
            runs={runs.data}
            loading={runs.isLoading}
            activeRunId={displayedRun?.id}
            onSelect={(run) => {
              stream.reset()
              applyRun.reset()
              setEditingText(null)
              setViewedRun(run)
            }}
          />
          </aside>
        </div>
      </ScrollArea>
    </>
  )
}

function ResultCard({
  agentName,
  isVideoKind,
  text,
  isStreaming,
  run,
  editingText,
  onStartEdit,
  onCancelEdit,
  onChangeEdit,
  onSaveEdit,
  savingEdit,
  canApply,
  applyLabel,
  onApply,
  applying,
  applied,
}: {
  agentName: string
  isVideoKind: boolean
  text: string
  isStreaming: boolean
  run: AgentRun | null
  editingText: string | null
  onStartEdit: () => void
  onCancelEdit: () => void
  onChangeEdit: (value: string) => void
  onSaveEdit: () => void
  savingEdit: boolean
  canApply: boolean
  applyLabel: string
  onApply: () => void
  applying: boolean
  applied: boolean
}) {
  const isEditing = editingText !== null
  const [showData, setShowData] = useState(false)

  async function copyText() {
    await navigator.clipboard.writeText(text)
    toast.success('Resposta copiada')
  }

  async function copyData() {
    if (!run?.output?.data) return
    await navigator.clipboard.writeText(JSON.stringify(run.output.data, null, 2))
    toast.success('Dados copiados')
  }

  return (
    <div className="flex items-start gap-3">
      <div className="flex size-10 shrink-0 items-center justify-center rounded-2xl bg-primary text-primary-foreground shadow-lg shadow-primary/20">
        <Sparkles className="size-4" />
      </div>
      <div className="min-w-0 flex-1 space-y-3 rounded-3xl border bg-card/90 px-4 py-4 shadow-sm shadow-slate-950/[0.04]">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex flex-wrap items-center gap-2 text-sm">
            <span className="font-semibold">{agentName}</span>
            {isStreaming ? (
              <span className="text-xs text-muted-foreground">gerando resposta…</span>
            ) : run ? (
              <span className="text-xs text-muted-foreground">
                <RelativeTime value={run.updated_at} />
              </span>
            ) : null}
            {run?.status === 'failed' ? (
              <Badge variant="outline" className="border-rose-200 bg-rose-50 text-rose-700">
                Falhou
              </Badge>
            ) : null}
          </div>
          {!isStreaming && run && !isEditing && !isVideoKind ? (
            <div className="flex items-center gap-1">
              <Button variant="ghost" size="icon-xs" onClick={copyText}>
                <Copy className="size-3.5" />
              </Button>
              <Button variant="ghost" size="sm" onClick={onStartEdit}>
                <Pencil className="size-4" />
                Editar
              </Button>
            </div>
          ) : null}
        </div>

        {isVideoKind ? (
          run?.output?.video_url ? (
            <RunVideoPlayer runId={run.id} />
          ) : run?.status === 'failed' ? null : (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="size-4 animate-spin" />
              Gerando vídeo… isso pode levar alguns minutos.
            </div>
          )
        ) : isEditing ? (
          <div className="space-y-2">
            <Textarea
              value={editingText ?? ''}
              onChange={(event) => onChangeEdit(event.target.value)}
              className="min-h-32"
            />
            <div className="flex justify-end gap-2">
              <Button variant="outline" size="sm" onClick={onCancelEdit}>
                Cancelar
              </Button>
              <Button size="sm" disabled={savingEdit} onClick={onSaveEdit}>
                {savingEdit ? (
                  <Loader2 className="size-4 animate-spin" />
                ) : (
                  <CheckCircle2 className="size-4" />
                )}
                Salvar edição
              </Button>
            </div>
          </div>
        ) : (
          <p className="whitespace-pre-wrap text-sm leading-7">
            {text || (isStreaming ? '' : 'Sem resposta.')}
            {isStreaming ? (
              <span className="ml-0.5 inline-block h-4 w-1.5 animate-pulse bg-foreground align-middle" />
            ) : null}
          </p>
        )}

        {!isStreaming && run?.output?.data ? (
          <div className="rounded-2xl border bg-muted/40">
            <button
              type="button"
              onClick={() => setShowData((open) => !open)}
              className="flex w-full items-center justify-between px-3 py-2 text-xs font-medium text-muted-foreground hover:text-foreground"
            >
              <span className="flex items-center gap-1.5">
                <ChevronDown
                  className={cn('size-3 transition-transform', showData && 'rotate-180')}
                />
                Dados estruturados
              </span>
              {showData ? (
                <span onClick={(event) => event.stopPropagation()}>
                  <Button variant="ghost" size="icon-xs" onClick={copyData}>
                    <Copy className="size-3.5" />
                  </Button>
                </span>
              ) : null}
            </button>
            {showData ? (
              <pre className="overflow-x-auto border-t px-3 py-2.5 text-xs">
                {JSON.stringify(run.output.data, null, 2)}
              </pre>
            ) : null}
          </div>
        ) : null}

        {canApply && !isEditing ? (
          <div className="flex items-center gap-2.5 border-t pt-3">
            <Button size="sm" className="rounded-xl" disabled={applying} onClick={onApply}>
              {applying ? (
                <Loader2 className="size-4 animate-spin" />
              ) : (
                <Wand2 className="size-4" />
              )}
              {applyLabel}
            </Button>
            {applied ? (
              <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2 py-0.5 text-xs font-medium text-emerald-700 ring-1 ring-emerald-200 dark:bg-emerald-950 dark:text-emerald-400 dark:ring-emerald-900">
                <CheckCircle2 className="size-3" />
                Aplicado
              </span>
            ) : null}
          </div>
        ) : null}
      </div>
    </div>
  )
}

function RunVideoPlayer({ runId }: { runId: string }) {
  const [blobUrl, setBlobUrl] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    let objectUrl: string | null = null
    let cancelled = false
    setLoading(true)
    setFailed(false)
    fetchAgentRunVideo(runId)
      .then((blob) => {
        if (cancelled) return
        objectUrl = URL.createObjectURL(blob)
        setBlobUrl(objectUrl)
      })
      .catch(() => {
        if (!cancelled) setFailed(true)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
      if (objectUrl) URL.revokeObjectURL(objectUrl)
    }
  }, [runId])

  if (loading) return <div className="h-64 w-36 animate-pulse rounded-lg bg-muted" />
  if (failed || !blobUrl) {
    return (
      <p className="text-sm text-destructive">
        Não foi possível carregar o vídeo — o OpenAI expira o conteúdo ~48h após a geração.
      </p>
    )
  }
  return <video controls src={blobUrl} className="w-full max-w-64 rounded-lg border bg-black" />
}

type ProductImageOption = {
  key: string
  url: string
  productId: string
  productName: string
  /** Posição da foto dentro das variações do mesmo produto (1-based), só
   * pra dar contexto visual — não é usado como identidade de seleção. */
  index: number
  total: number
}

function CatalogImagePicker({
  value,
  onChange,
  maxImages,
}: {
  value: string[]
  onChange: (urls: string[]) => void
  /** `undefined` = sem limite (ex: OpenRouter, que aceita várias imagens
   * dependendo do modelo). `1` trava seleção única (ex: Sora). */
  maxImages?: number
}) {
  const [open, setOpen] = useState(false)
  const [search, setSearch] = useState('')
  const products = useProducts(search, true, 24, 0)
  const options: ProductImageOption[] = (products.data?.items ?? []).flatMap((product) => {
    const images = productImages(product)
    return images.map((image, index) => ({
      key: `${product.id}:${image.url}`,
      url: image.url,
      productId: product.id,
      productName: product.name ?? 'Produto sem nome',
      index: index + 1,
      total: images.length,
    }))
  })
  const atLimit = maxImages !== undefined && value.length >= maxImages
  const selectedOptions = value.map((url) => options.find((option) => option.url === url)).filter(Boolean) as ProductImageOption[]
  const limitLabel = maxImages === 1 ? '1 foto' : maxImages ? `até ${maxImages} fotos` : 'múltiplas fotos'

  function toggle(url: string) {
    if (value.includes(url)) {
      onChange(value.filter((selected) => selected !== url))
      return
    }
    if (maxImages === 1) {
      onChange([url])
      setOpen(false)
      return
    }
    if (atLimit) return
    onChange([...value, url])
  }

  return (
    <>
      <div className="rounded-3xl border bg-card/86 p-3 shadow-sm shadow-slate-950/[0.035]">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="flex items-start gap-3">
            <div className="flex size-12 shrink-0 items-center justify-center rounded-2xl bg-primary text-primary-foreground shadow-lg shadow-primary/20">
              <ImageIcon className="size-5" />
            </div>
            <div>
              <p className="text-sm font-semibold">Fotos do produto</p>
              <p className="mt-0.5 text-xs leading-5 text-muted-foreground">
                {maxImages === 1
                  ? 'Sora usa uma imagem principal como referência.'
                  : `Este provedor aceita ${limitLabel} como referência visual.`}
              </p>
            </div>
          </div>
          <Button type="button" className="rounded-2xl" onClick={() => setOpen(true)}>
            <ImageIcon className="size-4" />
            Escolher fotos
          </Button>
        </div>

        {value.length > 0 ? (
          <div className="mt-3 grid gap-2 sm:grid-cols-4">
            {value.slice(0, 4).map((url, index) => (
              <div key={url} className="group relative overflow-hidden rounded-2xl border bg-muted">
                <img src={url} alt="" className="aspect-square w-full object-cover" />
                <button
                  type="button"
                  className="absolute right-2 top-2 flex size-7 items-center justify-center rounded-full bg-black/60 text-white opacity-0 transition group-hover:opacity-100"
                  onClick={() => toggle(url)}
                  aria-label="Remover foto"
                >
                  <X className="size-4" />
                </button>
                <span className="absolute bottom-2 left-2 rounded-full bg-black/65 px-2 py-0.5 text-[11px] font-medium text-white">
                  #{index + 1}
                </span>
              </div>
            ))}
            {value.length > 4 ? (
              <button
                type="button"
                onClick={() => setOpen(true)}
                className="flex aspect-square items-center justify-center rounded-2xl border border-dashed bg-muted/25 text-sm font-medium text-muted-foreground"
              >
                +{value.length - 4}
              </button>
            ) : null}
          </div>
        ) : (
          <button
            type="button"
            onClick={() => setOpen(true)}
            className="mt-3 flex min-h-28 w-full flex-col items-center justify-center gap-2 rounded-2xl border border-dashed bg-muted/25 text-center transition hover:bg-muted"
          >
            <ImageIcon className="size-6 text-muted-foreground" />
            <span className="text-sm font-medium">Nenhuma foto selecionada</span>
            <span className="text-xs text-muted-foreground">Escolha imagens do catálogo para liberar a geração.</span>
          </button>
        )}
      </div>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="flex max-h-[88vh] w-full max-w-6xl flex-col overflow-hidden rounded-3xl p-0 sm:max-w-6xl">
          <DialogHeader className="dark-panel relative overflow-hidden rounded-none border-0 px-5 py-5">
            <div className="surface-glow absolute right-8 top-0 h-32 w-32 rounded-full bg-violet-400/20 blur-3xl" />
            <DialogTitle className="relative text-white">Selecionar fotos do catálogo</DialogTitle>
            <DialogDescription>
              Escolha {limitLabel}. Todas as fotos e variações de cada produto aparecem aqui.
            </DialogDescription>
          </DialogHeader>

          <div className="grid min-h-0 flex-1 lg:grid-cols-[minmax(0,1fr)_320px]">
            <div className="flex min-h-0 flex-col">
              <div className="border-b bg-background/80 px-4 py-3 backdrop-blur">
                <div className="relative">
                  <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    value={search}
                    onChange={(event) => setSearch(event.target.value)}
                    placeholder="Buscar produto por nome ou código..."
                    className="h-11 rounded-2xl bg-card pl-9"
                    autoFocus
                  />
                </div>
              </div>

              <div className="min-h-0 flex-1 overflow-y-auto p-4">
                {products.isLoading ? (
                  <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-4 xl:grid-cols-5">
                    {Array.from({ length: 10 }).map((_, index) => (
                      <div key={index} className="aspect-[0.78] animate-pulse rounded-3xl bg-muted" />
                    ))}
                  </div>
                ) : options.length === 0 ? (
                  <EmptyState
                    icon={ImageOff}
                    title="Nenhum produto com foto"
                    description="Ajuste a busca ou sincronize produtos com mídia no catálogo."
                  />
                ) : (
                  <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-4 xl:grid-cols-5">
                    {options.map((option) => {
                      const selected = value.includes(option.url)
                      return (
                        <button
                          key={option.key}
                          type="button"
                          disabled={!selected && atLimit}
                          onClick={() => toggle(option.url)}
                          className={cn(
                            'group relative overflow-hidden rounded-3xl border bg-card p-2 text-left shadow-sm transition hover:-translate-y-0.5 hover:border-primary/35 hover:shadow-md disabled:cursor-not-allowed disabled:opacity-40',
                            selected && 'border-primary bg-primary/5 ring-2 ring-primary/25',
                          )}
                        >
                          <div className="relative overflow-hidden rounded-2xl bg-muted">
                            {selected ? (
                              <span className="absolute right-2 top-2 z-10 flex size-7 items-center justify-center rounded-full bg-primary text-primary-foreground shadow-lg">
                                <Check className="size-4" />
                              </span>
                            ) : null}
                            {option.total > 1 ? (
                              <span className="absolute left-2 top-2 z-10 rounded-full bg-black/65 px-2 py-0.5 text-[10px] font-medium text-white">
                                {option.index}/{option.total}
                              </span>
                            ) : null}
                            <img
                              src={option.url}
                              alt=""
                              className="aspect-square w-full object-cover transition duration-300 group-hover:scale-105"
                            />
                          </div>
                          <p className="mt-2 line-clamp-2 min-h-8 text-xs font-medium leading-4">
                            {option.productName}
                          </p>
                        </button>
                      )
                    })}
                  </div>
                )}
              </div>
            </div>

            <aside className="border-t bg-muted/25 p-4 lg:border-l lg:border-t-0">
              <div className="sticky top-0 space-y-4">
                <div>
                  <p className="text-sm font-semibold">Selecionadas</p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    {value.length} de {maxImages ?? 'várias'} foto(s)
                  </p>
                </div>

                {value.length === 0 ? (
                  <div className="rounded-3xl border border-dashed bg-card/70 p-4 text-center text-sm text-muted-foreground">
                    Escolha uma imagem no grid.
                  </div>
                ) : (
                  <div className="grid gap-3">
                    {value.map((url, index) => {
                      const option = selectedOptions.find((item) => item.url === url)
                      return (
                        <div key={url} className="overflow-hidden rounded-3xl border bg-card shadow-sm">
                          <img src={url} alt="" className="aspect-video w-full object-cover" />
                          <div className="flex items-center justify-between gap-3 p-3">
                            <div className="min-w-0">
                              <p className="truncate text-xs font-medium">
                                {option?.productName ?? `Foto ${index + 1}`}
                              </p>
                              <p className="text-[11px] text-muted-foreground">Referência #{index + 1}</p>
                            </div>
                            <Button
                              type="button"
                              variant="ghost"
                              size="icon-sm"
                              onClick={() => toggle(url)}
                            >
                              <X className="size-4" />
                            </Button>
                          </div>
                        </div>
                      )
                    })}
                  </div>
                )}
              </div>
            </aside>
          </div>

          <DialogFooter className="border-t bg-background/90 px-4 py-3 backdrop-blur">
            {value.length > 0 ? (
              <Button type="button" variant="outline" size="sm" onClick={() => onChange([])}>
                Limpar seleção
              </Button>
            ) : null}
            <Button type="button" size="sm" className="rounded-xl" onClick={() => setOpen(false)}>
              Concluído
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}

const RUN_STATUS_META: Record<string, { label: string; icon: typeof Clock; className: string }> = {
  completed: { label: 'Concluído', icon: CheckCircle2, className: 'text-emerald-600' },
  failed: { label: 'Falhou', icon: XCircle, className: 'text-rose-600' },
  running: { label: 'Executando', icon: Loader2, className: 'text-amber-600' },
  pending: { label: 'Pendente', icon: Clock, className: 'text-muted-foreground' },
}

function RunHistory({
  runs,
  loading,
  activeRunId,
  onSelect,
}: {
  runs: AgentRun[] | undefined
  loading: boolean
  activeRunId: string | undefined
  onSelect: (run: AgentRun) => void
}) {
  if (loading) return <div className="h-28 animate-pulse rounded-2xl bg-muted" />
  if (!runs || runs.length === 0) {
    return (
      <EmptyState
        icon={Clock}
        title="Sem execuções"
        description="As respostas geradas por este agente aparecerão aqui."
      />
    )
  }

  return (
    <div className="space-y-3">
      <div>
        <p className="text-sm font-semibold">Histórico</p>
        <p className="text-xs text-muted-foreground">{runs.length} execução(ões) registradas</p>
      </div>
      <div className="space-y-1.5">
        {runs.map((run) => {
          const meta = RUN_STATUS_META[run.status] ?? RUN_STATUS_META.pending
          const StatusIcon = meta.icon
          const active = activeRunId === run.id
          return (
            <button
              key={run.id}
              type="button"
              onClick={() => onSelect(run)}
              className={cn(
                'flex w-full items-start gap-2 rounded-2xl border bg-card/80 p-3 text-left text-xs transition hover:-translate-y-0.5 hover:bg-muted/50 hover:shadow-sm',
                active && 'border-primary/40 bg-primary/10 ring-1 ring-primary/15',
              )}
            >
              <StatusIcon className={cn('mt-0.5 size-3.5 shrink-0', meta.className)} />
              <div className="min-w-0 flex-1">
                <div className="flex items-center justify-between gap-2">
                  <span className="font-medium text-foreground/80">{meta.label}</span>
                  <RelativeTime value={run.created_at} />
                </div>
                <p className="mt-0.5 line-clamp-1 text-muted-foreground">{run.input.message}</p>
              </div>
            </button>
          )
        })}
      </div>
    </div>
  )
}

function ExtraContextEditor({
  rows,
  onChange,
}: {
  rows: { id: string; key: string; value: string }[]
  onChange: (rows: { id: string; key: string; value: string }[]) => void
}) {
  function updateRow(id: string, patch: Partial<{ key: string; value: string }>) {
    onChange(rows.map((row) => (row.id === id ? { ...row, ...patch } : row)))
  }

  function addRow() {
    onChange([...rows, { id: crypto.randomUUID(), key: '', value: '' }])
  }

  function removeRow(id: string) {
    onChange(rows.filter((row) => row.id !== id))
  }

  return (
    <div className="space-y-2 rounded-lg border bg-muted/25 p-2">
      <p className="text-xs text-muted-foreground">
        Informações extras que o agente deve considerar (opcional).
      </p>
      {rows.map((row) => (
        <div key={row.id} className="flex gap-2">
          <Input
            value={row.key}
            onChange={(event) => updateRow(row.id, { key: event.target.value })}
            placeholder="nome"
            className="text-xs"
          />
          <Input
            value={row.value}
            onChange={(event) => updateRow(row.id, { value: event.target.value })}
            placeholder="valor"
            className="text-xs"
          />
          <Button type="button" variant="ghost" size="icon" onClick={() => removeRow(row.id)}>
            <X className="size-4" />
          </Button>
        </div>
      ))}
      <Button type="button" variant="outline" size="sm" onClick={addRow}>
        <Plus className="size-4" />
        Adicionar
      </Button>
    </div>
  )
}

function AgentEditSheet({
  open,
  agent,
  companyId,
  canGoGlobal,
  onClose,
  onCreated,
}: {
  open: boolean
  agent: Agent | null
  companyId: string | undefined
  canGoGlobal: boolean
  onClose: () => void
  onCreated: (agent: Agent) => void
}) {
  const createAgent = useCreateAgent()
  const updateAgent = useUpdateAgent()

  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [kind, setKind] = useState<AgentKind>('chat')
  const [usageInstructions, setUsageInstructions] = useState('')
  const [systemPrompt, setSystemPrompt] = useState('')
  const [outputAction, setOutputAction] = useState<AgentOutputAction>('none')
  const [usesBrandArchetype, setUsesBrandArchetype] = useState(false)
  const [responseFormat, setResponseFormat] = useState<AgentResponseFormat>('text')
  const [isActive, setIsActive] = useState(true)
  const [isGlobal, setIsGlobal] = useState(false)
  const [showAdvanced, setShowAdvanced] = useState(false)
  const [model, setModel] = useState('')
  const [temperature, setTemperature] = useState('0.3')
  const [videoProvider, setVideoProvider] = useState<AgentVideoProvider>('openai')
  const [videoSize, setVideoSize] = useState<VideoSize>('720x1280')
  const [videoSeconds, setVideoSeconds] = useState<VideoSeconds>('8')

  useEffect(() => {
    if (!open) return
    setName(agent?.name ?? '')
    setDescription(agent?.description ?? '')
    setKind(agent?.kind ?? 'chat')
    setUsageInstructions(agent?.usage_instructions ?? '')
    setSystemPrompt(agent?.system_prompt ?? '')
    setOutputAction(agent?.output_action ?? 'none')
    setUsesBrandArchetype(agent?.uses_brand_archetype ?? false)
    setResponseFormat(agent?.response_format ?? 'text')
    setIsActive(agent?.is_active ?? true)
    setIsGlobal(agent?.is_global ?? false)
    setModel(agent?.model ?? '')
    setTemperature(String(agent?.temperature ?? 0.3))
    setVideoProvider(agent?.video_provider ?? 'openai')
    setVideoSize(agent?.video_size ?? '720x1280')
    setVideoSeconds(agent?.video_seconds ?? '8')
    setShowAdvanced(false)
  }, [open, agent])

  const isVideoKind = kind === 'image_to_video'

  function handleProviderChange(next: AgentVideoProvider) {
    setVideoProvider(next)
    // Modelo/formato/duração são específicos de cada provedor (ex.: um
    // model string do OpenRouter não é válido pra Sora) — trocar o
    // provedor sempre reseta os três, mesmo editando um agente existente,
    // pra evitar deixar uma combinação inconsistente para trás.
    setModel('')
    // Padrão deliberadamente o mais barato válido, não o de melhor
    // qualidade — 1080p/8s no Veo 3.1 já custou ~US$3,20 num teste só.
    // Quem quiser mais qualidade escolhe manualmente.
    setVideoSize(next === 'openai' ? '720x1280' : '720p')
    setVideoSeconds(next === 'openai' ? '8' : '4')
  }

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    const temperatureValue = Number(temperature)
    if (Number.isNaN(temperatureValue)) {
      toast.error('Temperatura inválida')
      return
    }
    const payload = {
      name,
      description: description || null,
      usage_instructions: usageInstructions || null,
      system_prompt: systemPrompt,
      kind,
      model: model || null,
      temperature: isVideoKind ? 0.3 : temperatureValue,
      uses_brand_archetype: usesBrandArchetype,
      response_format: isVideoKind ? 'text' : responseFormat,
      output_action: isVideoKind ? 'none' : outputAction,
      video_provider: isVideoKind ? videoProvider : 'openai',
      video_size: isVideoKind ? videoSize : null,
      video_seconds: isVideoKind ? videoSeconds : null,
      is_active: isActive,
      is_global: isGlobal,
    }

    if (agent) {
      updateAgent.mutate({ id: agent.id, data: payload }, { onSuccess: onClose })
    } else {
      if (!companyId) return
      const createPayload: AgentCreateInput = { ...payload, company_id: companyId }
      createAgent.mutate(createPayload, {
        onSuccess: (created) => {
          onCreated(created)
          onClose()
        },
      })
    }
  }

  const isPending = createAgent.isPending || updateAgent.isPending

  return (
    <Sheet open={open} onOpenChange={(nextOpen) => !nextOpen && onClose()}>
      <SheetContent className="overflow-y-auto data-[side=right]:w-full data-[side=right]:sm:max-w-none data-[side=right]:lg:w-[52vw]">
        <SheetHeader>
          <SheetTitle>{agent ? 'Editar agente' : 'Criar agente'}</SheetTitle>
          <SheetDescription>
            Defina as instruções do agente — sem precisar de deploy pra mudar o comportamento
            dele depois.
          </SheetDescription>
        </SheetHeader>

        <form className="space-y-4 px-4 pb-6" onSubmit={onSubmit}>
          <div className="dark-panel relative overflow-hidden rounded-3xl p-4">
            <div className="surface-glow absolute right-0 top-0 h-28 w-28 rounded-full bg-violet-400/20 blur-2xl" />
            <div className="relative flex items-start gap-3">
              <div className="flex size-11 items-center justify-center rounded-2xl bg-white text-slate-950">
                <Wand2 className="size-5" />
              </div>
              <div>
                <p className="text-sm font-semibold">Configuração do agente</p>
                <p className="mt-1 text-xs leading-5 text-white/55">
                  Deixe claro quando usar, como responder e se a saída vira uma ação aplicada no
                  sistema.
                </p>
              </div>
            </div>
          </div>

          <div className="grid gap-4 rounded-3xl border bg-card/82 p-4 shadow-sm sm:grid-cols-2">
          <div className="space-y-2">
            <Label htmlFor="agent-name">Nome</Label>
            <Input
              id="agent-name"
              value={name}
              onChange={(event) => setName(event.target.value)}
              placeholder="ex: Gerador de arquétipo de marca"
              required
            />
          </div>

          <div className="space-y-2">
            <Label>Tipo de agente</Label>
            <Select
              value={kind}
              onValueChange={(value) => setKind(value as AgentKind)}
              disabled={Boolean(agent)}
            >
              <SelectTrigger className="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="chat">Conversa (pergunta e resposta)</SelectItem>
                <SelectItem value="image_to_video">Imagem → vídeo</SelectItem>
              </SelectContent>
            </Select>
            {agent ? (
              <p className="text-xs text-muted-foreground">
                O tipo não pode ser alterado depois de criado.
              </p>
            ) : null}
          </div>
          </div>

          <div className="space-y-2 rounded-3xl border bg-card/82 p-4 shadow-sm">
            <Label htmlFor="agent-description">Descrição curta</Label>
            <Input
              id="agent-description"
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              placeholder="Uma frase explicando pra que serve"
            />
          </div>

          <div className="space-y-2 rounded-3xl border bg-card/82 p-4 shadow-sm">
            <Label htmlFor="agent-usage">Instruções para quem for usar</Label>
            <Textarea
              id="agent-usage"
              value={usageInstructions}
              onChange={(event) => setUsageInstructions(event.target.value)}
              placeholder="O que a pessoa deve escrever e o que esperar de volta"
              className="min-h-20"
            />
          </div>

          <div className="space-y-2 rounded-3xl border bg-card/82 p-4 shadow-sm">
            <Label htmlFor="agent-system-prompt">
              {isVideoKind ? 'Direção criativa base' : 'Como o agente deve se comportar'}
            </Label>
            <Textarea
              id="agent-system-prompt"
              value={systemPrompt}
              onChange={(event) => setSystemPrompt(event.target.value)}
              className="min-h-32"
              placeholder={
                isVideoKind
                  ? 'O que toda geração deste agente deve seguir: estilo de câmera, iluminação, o que preservar do produto...'
                  : 'Você é um agente que...'
              }
              required
            />
          </div>

          {isVideoKind ? (
            <>
              <div className="space-y-2">
                <Label>Provedor de vídeo</Label>
                <Select
                  value={videoProvider}
                  onValueChange={(value) => handleProviderChange(value as AgentVideoProvider)}
                >
                  <SelectTrigger className="w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="openai">OpenAI (Sora) — 1 imagem por vídeo</SelectItem>
                    <SelectItem value="openrouter">
                      OpenRouter (Veo, Kling, Wan...) — múltiplas imagens
                    </SelectItem>
                  </SelectContent>
                </Select>
                <p className="text-xs text-muted-foreground">
                  Trocar o provedor reseta Modelo/Formato/Duração abaixo — eles são
                  específicos de cada um.
                </p>
              </div>

              {videoProvider === 'openai' ? (
                <div className="grid gap-4 sm:grid-cols-2">
                  <div className="space-y-2">
                    <Label>Formato do vídeo</Label>
                    <Select
                      value={videoSize}
                      onValueChange={(value) => setVideoSize(value as VideoSize)}
                    >
                      <SelectTrigger className="w-full">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {VIDEO_SIZE_OPTIONS.map((option) => (
                          <SelectItem key={option.value} value={option.value}>
                            {option.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label>Duração</Label>
                    <Select
                      value={videoSeconds}
                      onValueChange={(value) => setVideoSeconds(value as VideoSeconds)}
                    >
                      <SelectTrigger className="w-full">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {VIDEO_SECONDS_OPTIONS.map((seconds) => (
                          <SelectItem key={seconds} value={seconds}>
                            {seconds}s
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                </div>
              ) : (
                <div className="grid gap-4 sm:grid-cols-2">
                  <div className="space-y-2">
                    <Label htmlFor="agent-video-size">Resolução</Label>
                    <Input
                      id="agent-video-size"
                      value={videoSize}
                      onChange={(event) => setVideoSize(event.target.value)}
                      placeholder="1080p"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="agent-video-seconds">Duração (segundos)</Label>
                    <Input
                      id="agent-video-seconds"
                      type="number"
                      min={1}
                      value={videoSeconds}
                      onChange={(event) => setVideoSeconds(event.target.value)}
                    />
                  </div>
                  <p className="text-xs text-muted-foreground sm:col-span-2">
                    Valores válidos dependem do modelo escolhido em "Modelo" nas configurações
                    avançadas (ex: google/veo-3.1).
                  </p>
                </div>
              )}
            </>
          ) : (
            <div className="space-y-2">
              <Label>O que fazer com o resultado</Label>
              <Select
                value={outputAction}
                onValueChange={(value) => setOutputAction(value as AgentOutputAction)}
              >
                <SelectTrigger className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {AGENT_OUTPUT_ACTIONS.map((action) => (
                    <SelectItem key={action.value} value={action.value}>
                      {action.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}

          <label className="flex items-center gap-2 rounded-lg border bg-muted/35 p-3 text-sm">
            <input
              type="checkbox"
              checked={usesBrandArchetype}
              onChange={(event) => setUsesBrandArchetype(event.target.checked)}
              className="size-4 accent-primary"
            />
            Usar o arquétipo de marca da empresa como contexto
            {isVideoKind ? (
              <span className="text-xs text-muted-foreground">
                (entra no prompt de geração do vídeo)
              </span>
            ) : null}
          </label>

          <label className="flex items-center gap-2 rounded-lg border bg-muted/35 p-3 text-sm">
            <input
              type="checkbox"
              checked={isActive}
              onChange={(event) => setIsActive(event.target.checked)}
              className="size-4 accent-primary"
            />
            Agente ativo
          </label>

          <label
            className={cn(
              'flex items-center gap-2 rounded-lg border bg-muted/35 p-3 text-sm',
              !canGoGlobal && 'opacity-50',
            )}
          >
            <input
              type="checkbox"
              checked={isGlobal}
              disabled={!canGoGlobal}
              onChange={(event) => setIsGlobal(event.target.checked)}
              className="size-4 accent-primary"
            />
            <Globe className="size-4 text-primary" />
            <span>
              Global (visível e executável por todas as empresas)
              {!canGoGlobal ? ' — só admins podem ativar' : ''}
            </span>
          </label>

          <div className="rounded-lg border">
            <button
              type="button"
              onClick={() => setShowAdvanced((open) => !open)}
              className="flex w-full items-center justify-between px-3 py-2.5 text-sm font-medium"
            >
              Configurações avançadas
              <ChevronDown
                className={cn('size-4 transition-transform', showAdvanced && 'rotate-180')}
              />
            </button>
            {showAdvanced ? (
              <div className="grid gap-4 border-t p-3 sm:grid-cols-3">
                <div className="space-y-2">
                  <Label htmlFor="agent-model">Modelo</Label>
                  <Input
                    id="agent-model"
                    value={model}
                    onChange={(event) => setModel(event.target.value)}
                    placeholder={
                      isVideoKind
                        ? videoProvider === 'openai'
                          ? 'sora-2 (padrão)'
                          : 'google/veo-3.1 (padrão)'
                        : 'padrão'
                    }
                  />
                </div>
                {!isVideoKind ? (
                  <>
                    <div className="space-y-2">
                      <Label htmlFor="agent-temperature">Temperatura</Label>
                      <Input
                        id="agent-temperature"
                        type="number"
                        min={0}
                        max={2}
                        step={0.1}
                        value={temperature}
                        onChange={(event) => setTemperature(event.target.value)}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>Formato de resposta</Label>
                      <Select
                        value={responseFormat}
                        onValueChange={(value) => setResponseFormat(value as AgentResponseFormat)}
                      >
                        <SelectTrigger className="w-full">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="text">Texto</SelectItem>
                          <SelectItem value="json">Dado estruturado</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                  </>
                ) : null}
              </div>
            ) : null}
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
