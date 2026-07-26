import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import {
  applyAgentRun,
  createAgent,
  deleteAgent,
  getAgentRun,
  getAgentRuns,
  getAgents,
  runAgent,
  updateAgent,
  updateAgentRunOutput,
} from '@/lib/api'
import { catalogKeys } from '@/hooks/use-catalog'
import type { AgentCreateInput, AgentRunRequestInput, AgentUpdateInput } from '@/types/api'

export const agentKeys = {
  agents: ['agents', 'list'] as const,
  runs: (agentId?: string) => ['agents', 'runs', agentId ?? 'all'] as const,
}

export function useAgents() {
  return useQuery({ queryKey: agentKeys.agents, queryFn: getAgents })
}

export function useAgentRuns(agentId?: string) {
  return useQuery({
    queryKey: agentKeys.runs(agentId),
    queryFn: () => getAgentRuns(agentId),
    enabled: Boolean(agentId),
  })
}

/** Polls a single run while it's still settling — used for
 * `kind="image_to_video"` runs, which come back `status="running"` from
 * `POST /run` immediately (no token stream to watch, unlike chat). */
export function usePollAgentRun(runId: string | null, enabled: boolean) {
  return useQuery({
    queryKey: ['agents', 'run', runId] as const,
    queryFn: () => getAgentRun(runId as string),
    enabled: Boolean(runId) && enabled,
    refetchInterval: (query) => {
      const status = query.state.data?.status
      return status === 'running' || status === 'pending' ? 4000 : false
    },
  })
}

/** Non-streaming run trigger — used for `kind="image_to_video"` agents,
 * which don't support `POST /run/stream` (there's no token to stream). */
export function useRunAgentOnce() {
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: AgentRunRequestInput }) => runAgent(id, data),
    onError: (error: Error) =>
      toast.error('Falha ao executar agente', { description: error.message }),
  })
}

export function useCreateAgent() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data: AgentCreateInput) => createAgent(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: agentKeys.agents })
      toast.success('Agente criado')
    },
    onError: (error: Error) => toast.error('Falha ao criar agente', { description: error.message }),
  })
}

export function useUpdateAgent() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: AgentUpdateInput }) => updateAgent(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: agentKeys.agents })
      toast.success('Agente atualizado')
    },
    onError: (error: Error) =>
      toast.error('Falha ao atualizar agente', { description: error.message }),
  })
}

export function useDeleteAgent() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => deleteAgent(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: agentKeys.agents })
      toast.success('Agente removido')
    },
    onError: (error: Error) => toast.error('Falha ao remover agente', { description: error.message }),
  })
}

export function useUpdateAgentRunOutput() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, text }: { id: string; text: string }) => updateAgentRunOutput(id, text),
    onSuccess: (run) => {
      queryClient.invalidateQueries({ queryKey: agentKeys.runs(run.agent_id) })
      queryClient.invalidateQueries({ queryKey: agentKeys.runs(undefined) })
      toast.success('Resultado atualizado')
    },
    onError: (error: Error) => toast.error('Falha ao salvar edição', { description: error.message }),
  })
}

export function useApplyAgentRun() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (runId: string) => applyAgentRun(runId),
    onSuccess: () => {
      // aplicar hoje só existe pra arquétipo de marca — invalida também essa
      // lista pra Configurações/qualquer outra tela refletir na hora.
      queryClient.invalidateQueries({ queryKey: catalogKeys.brandArchetypeProfiles })
      toast.success('Resultado aplicado')
    },
    onError: (error: Error) =>
      toast.error('Falha ao aplicar resultado', { description: error.message }),
  })
}
