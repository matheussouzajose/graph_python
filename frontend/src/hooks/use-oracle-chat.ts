import { useCallback, useEffect, useRef, useState } from 'react'
import { toast } from 'sonner'
import {
  createChatSession,
  getChatHistory,
  getChatSessions,
  streamChatMessage,
} from '@/lib/api'
import type { AskSource, ChatMessage, ChatSession } from '@/types/api'

export type UiChatMessage = {
  id: string
  role: 'user' | 'assistant'
  content: string
  route: 'LOCAL' | 'GLOBAL' | null
  generatedQuery: string | null
  sources: AskSource[] | null
  pending?: boolean
}

export function useOracleChat() {
  const [sessions, setSessions] = useState<ChatSession[]>([])
  const [activeSession, setActiveSession] = useState<ChatSession | null>(null)
  const [messages, setMessages] = useState<UiChatMessage[]>([])
  const [isStreaming, setIsStreaming] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const abortRef = useRef<AbortController | null>(null)

  const loadSessions = useCallback(async () => {
    const data = await getChatSessions()
    setSessions(data)
    return data
  }, [])

  const loadSession = useCallback(async (sessionId: string) => {
    const history = await getChatHistory(sessionId)
    setActiveSession(history.session)
    setMessages(history.messages.map(toUiMessage))
  }, [])

  useEffect(() => {
    loadSessions().catch((err: unknown) => {
      const message = err instanceof Error ? err.message : 'Falha ao carregar conversas'
      toast.error('Falha ao carregar conversas', { description: message })
    })
  }, [loadSessions])

  const newChat = useCallback(async () => {
    abortRef.current?.abort()
    setIsStreaming(false)
    setError(null)
    const session = await createChatSession('Nova conversa')
    setActiveSession(session)
    setMessages([])
    setSessions((current) => [session, ...current.filter((item) => item.id !== session.id)])
  }, [])

  const send = useCallback(
    async (content: string) => {
      const text = content.trim()
      if (!text || isStreaming) return

      let session = activeSession
      if (!session) {
        const createdSession = await createChatSession(text.slice(0, 80))
        session = createdSession
        setActiveSession(createdSession)
        setSessions((current) => [createdSession, ...current])
      }

      const assistantId = crypto.randomUUID()
      setMessages((current) => [
        ...current,
        {
          id: crypto.randomUUID(),
          role: 'user',
          content: text,
          route: null,
          generatedQuery: null,
          sources: null,
        },
        {
          id: assistantId,
          role: 'assistant',
          content: '',
          route: null,
          generatedQuery: null,
          sources: null,
          pending: true,
        },
      ])

      const controller = new AbortController()
      abortRef.current = controller
      setIsStreaming(true)
      setError(null)

      try {
        await streamChatMessage(
          session.id,
          text,
          5,
          (event) => {
            setMessages((current) =>
              current.map((message) => {
                if (message.id !== assistantId) return message
                if (event.type === 'route') {
                  return { ...message, route: event.route ?? null }
                }
                if (event.type === 'meta') {
                  return {
                    ...message,
                    generatedQuery: event.generated_query ?? message.generatedQuery,
                    sources: event.sources ?? message.sources,
                  }
                }
                if (event.type === 'token') {
                  return { ...message, content: message.content + (event.text ?? '') }
                }
                if (event.type === 'replace') {
                  return { ...message, content: event.text ?? message.content }
                }
                if (event.type === 'error') {
                  return {
                    ...message,
                    content: event.message ?? 'Falha ao responder.',
                    pending: false,
                  }
                }
                if (event.type === 'done') {
                  return { ...message, pending: false }
                }
                return message
              }),
            )
          },
          controller.signal,
        )
        await loadSessions()
      } catch (err) {
        if (controller.signal.aborted) return
        const message = err instanceof Error ? err.message : 'Falha ao conversar'
        setError(message)
        setMessages((current) =>
          current.map((item) =>
            item.id === assistantId ? { ...item, content: message, pending: false } : item,
          ),
        )
      } finally {
        if (!controller.signal.aborted) setIsStreaming(false)
      }
    },
    [activeSession, isStreaming, loadSessions],
  )

  const stop = useCallback(() => {
    abortRef.current?.abort()
    setIsStreaming(false)
    setMessages((current) =>
      current.map((message) => (message.pending ? { ...message, pending: false } : message)),
    )
  }, [])

  return {
    sessions,
    activeSession,
    messages,
    isStreaming,
    error,
    loadSession,
    newChat,
    send,
    stop,
  }
}

function toUiMessage(message: ChatMessage): UiChatMessage {
  return {
    id: message.id,
    role: message.role,
    content: message.content,
    route: message.route,
    generatedQuery: message.generated_query,
    sources: message.sources,
  }
}
