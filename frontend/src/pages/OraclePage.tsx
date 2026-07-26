import { useCallback, useEffect, useRef, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import {
  Bot,
  ChevronDown,
  Copy,
  MessageSquare,
  Plus,
  Send,
  Sparkles,
  Square,
  User,
} from 'lucide-react'
import { toast } from 'sonner'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Textarea } from '@/components/ui/textarea'
import { RelativeTime } from '@/components/shared/RelativeTime'
import { useOracleChat, type UiChatMessage } from '@/hooks/use-oracle-chat'
import { cn } from '@/lib/utils'
import type { AskSource } from '@/types/api'

const SUGGESTIONS = [
  'Quais são os produtos mais vendidos?',
  'Quais clientes parecem estar em risco?',
  'Compare vendas por estado.',
  'Quais oportunidades de cross-sell temos?',
]

export function OraclePage() {
  const [question, setQuestion] = useState('')
  const bottomRef = useRef<HTMLDivElement | null>(null)
  const commandQuestionHandled = useRef(false)
  const location = useLocation()
  const navigate = useNavigate()
  const chat = useOracleChat()

  const handleAsk = useCallback(async (text: string) => {
    const trimmed = text.trim()
    if (!trimmed || chat.isStreaming) return
    setQuestion('')
    await chat.send(trimmed)
  }, [chat])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [chat.messages, chat.isStreaming])

  useEffect(() => {
    const commandQuestion =
      typeof location.state === 'object' &&
      location.state !== null &&
      'question' in location.state &&
      typeof location.state.question === 'string'
        ? location.state.question
        : ''

    if (!commandQuestion || commandQuestionHandled.current) return
    commandQuestionHandled.current = true
    navigate(location.pathname, { replace: true })
    void handleAsk(commandQuestion)
  }, [handleAsk, location.pathname, location.state, navigate])

  return (
    <div className="flex min-h-[calc(100vh-7rem)] flex-col gap-4">
      <section className="dark-panel relative overflow-hidden rounded-3xl p-5 sm:p-6">
        <div className="surface-glow absolute right-10 top-0 h-44 w-44 rounded-full bg-teal-400/18 blur-3xl" />
        <div className="absolute -bottom-20 left-1/3 h-44 w-44 rounded-full bg-violet-400/12 blur-3xl" />
        <div className="relative grid gap-5 lg:grid-cols-[1fr_360px] lg:items-center">
          <div>
            <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/8 px-3 py-1.5 text-xs text-teal-100">
              <Bot className="size-3.5" />
              Copiloto analítico
            </div>
            <h2 className="mt-4 max-w-2xl text-3xl font-semibold tracking-normal">
              Pergunte como gestor, receba resposta com contexto operacional.
            </h2>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-white/55">
              O chat consulta dados, histórico e fontes para transformar dúvida comercial em
              decisão rastreável.
            </p>
          </div>
          <div className="rounded-2xl border border-white/10 bg-white/[0.075] p-4">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-xs text-white/45">Sessões salvas</p>
                <p className="mt-1 text-2xl font-semibold">{chat.sessions.length}</p>
              </div>
              <Button
                variant="outline"
                size="sm"
                className="border-white/10 bg-white/[0.08] text-white hover:bg-white/[0.14]"
                onClick={() => chat.newChat()}
              >
                <Plus className="size-4" />
                Nova
              </Button>
            </div>
            <div className="mt-4 grid gap-2">
              {SUGGESTIONS.slice(0, 2).map((suggestion) => (
                <button
                  key={suggestion}
                  type="button"
                  disabled={chat.isStreaming}
                  onClick={() => handleAsk(suggestion)}
                  className="rounded-xl border border-white/10 bg-white/[0.06] px-3 py-2 text-left text-xs text-white/72 transition hover:bg-white/[0.1] disabled:opacity-50"
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </div>
        </div>
      </section>

      <div className="grid min-h-0 flex-1 gap-4 lg:grid-cols-[280px_1fr]">
        <aside className="hidden min-h-0 overflow-hidden rounded-2xl border bg-card/82 shadow-sm shadow-slate-950/[0.035] backdrop-blur lg:flex lg:flex-col">
          <div className="border-b px-3 py-3">
            <p className="text-sm font-medium">Conversas</p>
            <p className="text-xs text-muted-foreground">Histórico salvo no backend.</p>
          </div>
          <ScrollArea className="min-h-0 flex-1">
            <div className="space-y-1 p-2">
              {chat.sessions.length === 0 ? (
                <p className="px-2 py-3 text-sm text-muted-foreground">Nenhuma conversa ainda.</p>
              ) : (
                chat.sessions.map((session) => (
                  <button
                    key={session.id}
                    type="button"
                    onClick={() => chat.loadSession(session.id)}
                    className={cn(
                      'block w-full rounded-lg px-3 py-2 text-left transition hover:bg-muted',
                      chat.activeSession?.id === session.id && 'bg-muted',
                    )}
                  >
                    <span className="block truncate text-sm font-medium">{session.title}</span>
                    <span className="block text-xs text-muted-foreground">
                      <RelativeTime value={session.updated_at} />
                    </span>
                  </button>
                ))
              )}
            </div>
          </ScrollArea>
        </aside>

        <div className="flex min-h-0 flex-col overflow-hidden rounded-3xl border bg-card/86 shadow-sm shadow-slate-950/[0.04] backdrop-blur">
          <ScrollArea className="min-h-0 flex-1">
            <div className="mx-auto flex w-full max-w-4xl flex-col gap-5 px-4 py-6">
              {chat.messages.length === 0 ? (
                <WelcomeState onAsk={handleAsk} disabled={chat.isStreaming} />
              ) : null}

              {chat.messages.map((message) => (
                <ChatBubble key={message.id} message={message} />
              ))}

              {chat.error ? <p className="text-sm text-destructive">{chat.error}</p> : null}
              <div ref={bottomRef} />
            </div>
          </ScrollArea>

          <div className="border-t bg-background/82 px-4 py-3 backdrop-blur-xl">
            <div className="mx-auto flex max-w-4xl items-end gap-2 rounded-2xl border bg-card/92 p-2 shadow-lg shadow-slate-950/[0.05]">
              <Textarea
                value={question}
                onChange={(event) => setQuestion(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === 'Enter' && !event.shiftKey) {
                    event.preventDefault()
                    handleAsk(question)
                  }
                }}
                placeholder="Pergunte sobre vendas, clientes, pedidos, produtos ou próximos passos..."
                rows={1}
                className="max-h-36 min-h-10 resize-none border-0 bg-transparent shadow-none focus-visible:ring-0"
              />
              {chat.isStreaming ? (
                <Button type="button" variant="outline" size="icon" onClick={chat.stop}>
                  <Square className="size-4" />
                </Button>
              ) : (
                <Button
                  type="button"
                  size="icon"
                  disabled={!question.trim()}
                  onClick={() => handleAsk(question)}
                >
                  <Send className="size-4" />
                </Button>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

function WelcomeState({
  onAsk,
  disabled,
}: {
  onAsk: (question: string) => void
  disabled: boolean
}) {
  return (
    <div className="flex min-h-[420px] flex-col items-center justify-center text-center">
      <div className="flex size-12 items-center justify-center rounded-xl bg-primary/10 text-primary ring-1 ring-primary/15">
        <Sparkles className="size-6" />
      </div>
      <h2 className="mt-4 text-xl font-semibold tracking-tight">O que vamos descobrir hoje?</h2>
      <p className="mt-2 max-w-xl text-sm leading-6 text-muted-foreground">
        O chat lembra o contexto desta conversa e consulta os dados da sua empresa.
      </p>
      <div className="mt-6 grid w-full max-w-2xl gap-2 sm:grid-cols-2">
        {SUGGESTIONS.map((suggestion) => (
          <button
            key={suggestion}
            type="button"
            disabled={disabled}
            onClick={() => onAsk(suggestion)}
            className="rounded-xl border bg-background p-3 text-left text-sm shadow-sm transition hover:bg-muted disabled:pointer-events-none disabled:opacity-50"
          >
            {suggestion}
          </button>
        ))}
      </div>
    </div>
  )
}

function ChatBubble({ message }: { message: UiChatMessage }) {
  if (message.role === 'user') {
    return (
      <div className="flex justify-end">
        <div className="flex max-w-[82%] items-start gap-2">
          <div className="rounded-2xl bg-primary px-4 py-2.5 text-sm leading-6 text-primary-foreground shadow-sm">
            {message.content}
          </div>
          <Avatar icon={User} tone="user" />
        </div>
      </div>
    )
  }

  return <AssistantBubble message={message} />
}

function AssistantBubble({ message }: { message: UiChatMessage }) {
  return (
    <div className="flex justify-start">
      <div className="flex max-w-[88%] items-start gap-2">
        <Avatar icon={Bot} tone="assistant" />
        <div className="min-w-0 space-y-3 rounded-2xl border bg-background px-4 py-3 text-sm leading-6 shadow-sm">
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-medium">Oráculo</span>
            {message.route ? (
              <Badge variant={message.route === 'GLOBAL' ? 'default' : 'secondary'}>
                {message.route}
              </Badge>
            ) : null}
            {message.pending ? (
              <span className="text-xs text-muted-foreground">pensando</span>
            ) : null}
          </div>

          <p className="whitespace-pre-wrap">
            {message.content || (message.pending ? '' : 'Sem resposta.')}
            {message.pending ? (
              <span className="ml-0.5 inline-block h-4 w-1.5 animate-pulse bg-foreground align-middle" />
            ) : null}
          </p>

          {message.generatedQuery ? <GeneratedQuery query={message.generatedQuery} /> : null}
          {message.sources && message.sources.length > 0 ? (
            <SourceList sources={message.sources} />
          ) : null}
        </div>
      </div>
    </div>
  )
}

function GeneratedQuery({ query }: { query: string }) {
  const [open, setOpen] = useState(false)

  async function copyQuery() {
    await navigator.clipboard.writeText(query)
    toast.success('Cypher copiado')
  }

  if (!open) {
    return (
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="flex items-center gap-1 text-xs text-muted-foreground underline decoration-dotted underline-offset-2 hover:text-foreground"
      >
        <ChevronDown className="size-3" />
        Ver consulta gerada (debug)
      </button>
    )
  }

  return (
    <div className="rounded-xl border bg-muted/55">
      <div className="flex items-center justify-between gap-2 border-b px-3 py-2">
        <button
          type="button"
          onClick={() => setOpen(false)}
          className="text-xs font-medium text-muted-foreground hover:text-foreground"
        >
          Cypher gerado (debug)
        </button>
        <Button type="button" variant="ghost" size="icon-xs" onClick={copyQuery}>
          <Copy className="size-3.5" />
        </Button>
      </div>
      <pre className="overflow-x-auto p-3 text-xs">
        <code>{query}</code>
      </pre>
    </div>
  )
}

function SourceList({ sources }: { sources: AskSource[] }) {
  return (
    <div>
      <p className="mb-1 text-xs font-medium text-muted-foreground">Fontes</p>
      <ul className="space-y-1 text-xs">
        {sources.map((source, index) => (
          <li key={index} className="flex justify-between gap-3 rounded-md border bg-card px-2 py-1">
            <span className="min-w-0 truncate">
              {source.order_code
                ? `Pedido #${source.order_code}`
                : source.product_code
                  ? `Produto (código ${source.product_code})`
                  : source.customer_name
                    ? `Cliente: ${source.customer_name}`
                    : '—'}
            </span>
            <span className="shrink-0 text-muted-foreground">
              score {source.score?.toFixed(3) ?? '—'}
            </span>
          </li>
        ))}
      </ul>
    </div>
  )
}

function Avatar({
  icon: Icon,
  tone,
}: {
  icon: typeof MessageSquare
  tone: 'assistant' | 'user'
}) {
  return (
    <div
      className={cn(
        'flex size-8 shrink-0 items-center justify-center rounded-full ring-1',
        tone === 'assistant'
          ? 'bg-primary/10 text-primary ring-primary/15'
          : 'bg-muted text-muted-foreground ring-border',
      )}
    >
      <Icon className="size-4" />
    </div>
  )
}
