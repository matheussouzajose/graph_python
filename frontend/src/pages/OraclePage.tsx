import { useEffect, useState } from 'react'
import { Compass, History, MessageSquareText, Send, Square } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Badge } from '@/components/ui/badge'
import { EmptyState } from '@/components/shared/EmptyState'
import { PageHeader } from '@/components/shared/PageHeader'
import { SectionCard } from '@/components/shared/SectionCard'
import { useAskOracleStream, type OracleResult } from '@/hooks/use-oracle-stream'
import type { AskSource } from '@/types/api'

interface HistoryEntry extends OracleResult {
  id: string
  question: string
  askedAt: string
}

const HISTORY_KEY = 'oraculo.history'
const HISTORY_LIMIT = 15

const SUGGESTIONS = [
  'Quais são os produtos mais vendidos?',
  'Quais clientes parecem estar em risco?',
  'Quais produtos são parecidos com o produto mais vendido?',
  'Qual estado concentra mais pedidos?',
]

function loadHistory(): HistoryEntry[] {
  try {
    const raw = localStorage.getItem(HISTORY_KEY)
    return raw ? (JSON.parse(raw) as HistoryEntry[]) : []
  } catch {
    return []
  }
}

export function OraclePage() {
  const [question, setQuestion] = useState('')
  const [history, setHistory] = useState<HistoryEntry[]>(() => loadHistory())
  const [currentQuestion, setCurrentQuestion] = useState<string | null>(null)
  const [viewingEntry, setViewingEntry] = useState<HistoryEntry | null>(null)
  const oracle = useAskOracleStream()

  useEffect(() => {
    localStorage.setItem(HISTORY_KEY, JSON.stringify(history))
  }, [history])

  function handleAsk(text: string) {
    if (!text.trim() || oracle.isStreaming) return
    setViewingEntry(null)
    setCurrentQuestion(text)
    setQuestion('')
    oracle.ask(text, 5, (result) => {
      const entry: HistoryEntry = {
        id: crypto.randomUUID(),
        question: text,
        askedAt: new Date().toISOString(),
        ...result,
      }
      setHistory((prev) => [entry, ...prev].slice(0, HISTORY_LIMIT))
    })
  }

  const displayed: (OracleResult & { question: string }) | null = viewingEntry
    ? viewingEntry
    : currentQuestion
      ? {
          question: currentQuestion,
          route: oracle.route,
          answer: oracle.answer,
          sources: oracle.sources,
          generatedQuery: oracle.generatedQuery,
        }
      : null
  const isLiveView = !viewingEntry
  const showStreamingCursor = isLiveView && oracle.isStreaming

  return (
    <div className="space-y-6">
      <PageHeader
        title="Oráculo"
        description="Faça perguntas em linguagem natural e acompanhe a resposta com fontes e consulta gerada."
        icon={Compass}
      />

      <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
        <div className="space-y-4">
          <SectionCard
            title="Pergunte em linguagem natural"
            description="O Oráculo decide entre busca local e consulta analítica no grafo."
            icon={Compass}
          >
            <div className="space-y-3">
              <Textarea
                placeholder="Ex: Quais produtos mais vendidos no último mês?"
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) handleAsk(question)
                }}
                rows={3}
              />
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex flex-wrap gap-1.5">
                  {SUGGESTIONS.map((s) => (
                    <button
                      key={s}
                      type="button"
                      onClick={() => setQuestion(s)}
                      className="rounded-md border bg-card px-2.5 py-1 text-xs text-muted-foreground shadow-sm hover:bg-muted"
                    >
                      {s}
                    </button>
                  ))}
                </div>
                {oracle.isStreaming ? (
                  <Button
                    variant="outline"
                    onClick={() => {
                      oracle.reset()
                      setCurrentQuestion(null)
                    }}
                  >
                    <Square className="size-4" />
                    Parar
                  </Button>
                ) : (
                  <Button disabled={!question.trim()} onClick={() => handleAsk(question)}>
                    <Send className="size-4" />
                    Perguntar
                  </Button>
                )}
              </div>
            </div>
          </SectionCard>

          {displayed ? (
            <SectionCard
              title={displayed.question}
              icon={MessageSquareText}
              actions={
                displayed.route ? (
                  <Badge variant={displayed.route === 'GLOBAL' ? 'default' : 'secondary'}>
                    {displayed.route}
                  </Badge>
                ) : null
              }
              contentClassName="space-y-4"
            >
              {isLiveView && oracle.error ? (
                <p className="text-sm text-destructive">{oracle.error}</p>
              ) : (
                <p className="whitespace-pre-wrap text-sm leading-relaxed">
                  {displayed.answer || (showStreamingCursor ? '' : 'Sem resposta.')}
                  {showStreamingCursor ? (
                    <span className="ml-0.5 inline-block h-4 w-1.5 animate-pulse bg-foreground align-middle" />
                  ) : null}
                </p>
              )}

              {displayed.generatedQuery ? (
                <div>
                  <p className="mb-1 text-xs font-medium text-muted-foreground">Cypher gerado</p>
                  <pre className="overflow-x-auto rounded-lg border bg-muted/65 p-3 text-xs">
                    <code>{displayed.generatedQuery}</code>
                  </pre>
                </div>
              ) : null}

              {displayed.sources && displayed.sources.length > 0 ? (
                <div>
                  <p className="mb-1 text-xs font-medium text-muted-foreground">Fontes</p>
                  <ul className="space-y-1 text-xs">
                    {displayed.sources.map((source: AskSource, i: number) => (
                      <li
                        key={i}
                        className="flex justify-between rounded-md border bg-card px-2 py-1"
                      >
                        <span>
                          {source.order_code
                            ? `Pedido #${source.order_code}`
                            : source.product_code
                              ? `Produto (código ${source.product_code})`
                              : source.customer_name
                                ? `Cliente: ${source.customer_name}`
                                : '—'}
                        </span>
                        <span className="text-muted-foreground">
                          score {source.score?.toFixed(3) ?? '—'}
                        </span>
                      </li>
                    ))}
                  </ul>
                </div>
              ) : null}
            </SectionCard>
          ) : (
            <EmptyState
              title="Nenhuma pergunta feita ainda"
              description="Escreva uma pergunta acima ou escolha uma sugestão para começar."
            />
          )}
        </div>

        <SectionCard title="Histórico" icon={History} className="h-fit" contentClassName="space-y-1">
          {history.length === 0 ? (
            <p className="text-sm text-muted-foreground">Suas últimas perguntas aparecem aqui.</p>
          ) : (
            history.map((entry) => (
              <button
                key={entry.id}
                type="button"
                onClick={() => {
                  setViewingEntry(entry)
                  setCurrentQuestion(null)
                }}
                className="block w-full truncate rounded-md border border-transparent px-2 py-1.5 text-left text-sm hover:border-border hover:bg-muted"
              >
                {entry.question}
              </button>
            ))
          )}
        </SectionCard>
      </div>
    </div>
  )
}
