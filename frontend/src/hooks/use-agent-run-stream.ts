import { useCallback, useRef, useState } from 'react'
import { streamAgentRun } from '@/lib/api'
import type { AgentRun } from '@/types/api'

interface AgentRunStreamState {
  isStreaming: boolean
  text: string
  run: AgentRun | null
  error: string | null
}

const INITIAL_STATE: AgentRunStreamState = {
  isStreaming: false,
  text: '',
  run: null,
  error: null,
}

/**
 * Consome `POST /agents/{id}/run/stream`. Estado local (não TanStack Query)
 * de propósito — aqui a UI precisa re-renderizar a cada token, não só
 * quando a promise resolve (mesmo raciocínio de `useAskOracleStream`).
 */
export function useAgentRunStream() {
  const [state, setState] = useState<AgentRunStreamState>(INITIAL_STATE)
  const abortRef = useRef<AbortController | null>(null)

  const start = useCallback(
    (
      agentId: string,
      message: string,
      variables: Record<string, unknown>,
      onDone?: (run: AgentRun) => void,
    ) => {
      abortRef.current?.abort()
      const controller = new AbortController()
      abortRef.current = controller

      let acc = ''
      setState({ ...INITIAL_STATE, isStreaming: true })

      streamAgentRun(
        agentId,
        message,
        variables,
        (event) => {
          if (event.type === 'token') {
            acc += event.text ?? ''
            setState({ isStreaming: true, text: acc, run: null, error: null })
          } else if (event.type === 'error') {
            setState({
              isStreaming: false,
              text: acc,
              run: null,
              error: event.message ?? 'Erro desconhecido',
            })
          } else if (event.type === 'done' && event.run) {
            setState({ isStreaming: false, text: acc, run: event.run, error: null })
            onDone?.(event.run)
          }
        },
        controller.signal,
      ).catch((err: unknown) => {
        if (controller.signal.aborted) return
        const message = err instanceof Error ? err.message : 'Falha ao executar agente'
        setState((prev) => ({ ...prev, isStreaming: false, error: message }))
      })
    },
    [],
  )

  const stop = useCallback(() => {
    abortRef.current?.abort()
    setState((prev) => ({ ...prev, isStreaming: false }))
  }, [])

  const reset = useCallback(() => {
    abortRef.current?.abort()
    setState(INITIAL_STATE)
  }, [])

  return { ...state, start, stop, reset }
}
