import { useCallback, useRef, useState } from 'react'
import { streamOracleAsk } from '@/lib/api'
import type { AskSource } from '@/types/api'

export interface OracleResult {
  route: 'LOCAL' | 'GLOBAL' | null
  answer: string
  sources: AskSource[] | null
  generatedQuery: string | null
}

interface OracleStreamState extends OracleResult {
  isStreaming: boolean
  error: string | null
}

const INITIAL_STATE: OracleStreamState = {
  isStreaming: false,
  route: null,
  answer: '',
  sources: null,
  generatedQuery: null,
  error: null,
}

/**
 * Consome `POST /rag/ask/stream`. Usa estado local (não TanStack Query) de
 * propósito — React Query modela "uma resposta que chega inteira", e aqui a
 * UI precisa re-renderizar a cada token, não só quando a promise resolve.
 *
 * `resultRef` acumula os campos fora do ciclo de `setState` porque o
 * callback do evento `done` precisa do valor final (`answer` completo,
 * `sources`, etc.) pra devolver pro chamador via `onDone` — ler `state`
 * dentro do próprio callback do evento correria risco de pegar um valor
 * desatualizado (closures presas na render em que `ask` foi criado).
 */
export function useAskOracleStream() {
  const [state, setState] = useState<OracleStreamState>(INITIAL_STATE)
  const abortRef = useRef<AbortController | null>(null)

  const ask = useCallback(
    (question: string, topK = 5, onDone?: (result: OracleResult) => void) => {
      abortRef.current?.abort()
      const controller = new AbortController()
      abortRef.current = controller

      const acc: OracleResult = { route: null, answer: '', sources: null, generatedQuery: null }
      setState({ ...INITIAL_STATE, isStreaming: true })

      streamOracleAsk(
        question,
        topK,
        (event) => {
          switch (event.type) {
            case 'route':
              acc.route = event.route ?? null
              break
            case 'meta':
              if (event.sources) acc.sources = event.sources
              if (event.generated_query) acc.generatedQuery = event.generated_query
              break
            case 'token':
              acc.answer += event.text ?? ''
              break
            case 'error':
              setState({ ...acc, isStreaming: false, error: event.message ?? 'Erro desconhecido' })
              return
            case 'done':
              setState({ ...acc, isStreaming: false, error: null })
              onDone?.(acc)
              return
          }
          setState({ ...acc, isStreaming: true, error: null })
        },
        controller.signal,
      ).catch((err: unknown) => {
        if (controller.signal.aborted) return
        const message = err instanceof Error ? err.message : 'Falha ao perguntar'
        setState({ ...acc, isStreaming: false, error: message })
      })
    },
    [],
  )

  const reset = useCallback(() => {
    abortRef.current?.abort()
    setState(INITIAL_STATE)
  }, [])

  return { ...state, ask, reset }
}
