import { useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import {
  recommendByCustomer,
  recommendByProduct,
  syncIntegration,
  triggerAlgorithmsRun,
  triggerEmbeddingsRun,
  triggerGraphSync,
} from '@/lib/api'
import { dashboardKeys } from '@/hooks/use-dashboard'
import type { TriggerResponse } from '@/types/api'

function describeTrigger(response: TriggerResponse): { title: string; description?: string } {
  if (response.status === 'already_running') {
    return {
      title: 'Já existe uma execução em andamento',
      description: 'Aguarde a atual terminar antes de disparar outra.',
    }
  }
  return { title: 'Ação disparada com sucesso', description: 'Processando em segundo plano.' }
}

/** Jobs em background não têm callback de conclusão — refetch imediato pega o
 * status "already_running", e um segundo refetch alguns segundos depois tem
 * boa chance de já pegar o resultado de jobs rápidos (poucos pedidos/produtos).
 * Para volumes grandes o usuário só vai ver o resultado ao atualizar a Home
 * de novo mais tarde — não há um endpoint de progresso para fazer polling. */
function useRefreshAfterTrigger() {
  const queryClient = useQueryClient()
  return () => {
    queryClient.invalidateQueries({ queryKey: dashboardKeys.overview })
    queryClient.invalidateQueries({ queryKey: dashboardKeys.syncStatus })
    setTimeout(() => {
      queryClient.invalidateQueries({ queryKey: dashboardKeys.overview })
      queryClient.invalidateQueries({ queryKey: dashboardKeys.syncStatus })
    }, 6000)
  }
}

export function useSyncIntegrationAction() {
  const refresh = useRefreshAfterTrigger()
  return useMutation({
    mutationFn: (integrationId: string) => syncIntegration(integrationId),
    onSuccess: (response) => {
      const { title, description } = describeTrigger(response)
      toast.success(title, { description })
      refresh()
    },
    onError: (error: Error) => toast.error('Falha ao sincronizar pedidos', { description: error.message }),
  })
}

export function useGraphSyncAction() {
  const refresh = useRefreshAfterTrigger()
  return useMutation({
    mutationFn: () => triggerGraphSync(),
    onSuccess: (response) => {
      const { title, description } = describeTrigger(response)
      toast.success(title, { description })
      refresh()
    },
    onError: (error: Error) =>
      toast.error('Falha ao projetar pedidos no grafo', { description: error.message }),
  })
}

export function useRunAlgorithmsAction() {
  const refresh = useRefreshAfterTrigger()
  return useMutation({
    mutationFn: () => triggerAlgorithmsRun(),
    onSuccess: (response) => {
      const { title, description } = describeTrigger(response)
      toast.success(title, { description })
      refresh()
    },
    onError: (error: Error) =>
      toast.error('Falha ao rodar algoritmos', { description: error.message }),
  })
}

export function useRunEmbeddingsAction() {
  const refresh = useRefreshAfterTrigger()
  return useMutation({
    mutationFn: () => triggerEmbeddingsRun(),
    onSuccess: (response) => {
      const { title, description } = describeTrigger(response)
      toast.success(title, { description })
      refresh()
    },
    onError: (error: Error) =>
      toast.error('Falha ao rodar embeddings', { description: error.message }),
  })
}

export function useRecommendByProduct() {
  return useMutation({
    mutationFn: ({ productId, limit }: { productId: string; limit?: number }) =>
      recommendByProduct(productId, limit),
    onError: (error: Error) =>
      toast.error('Falha ao buscar recomendações', { description: error.message }),
  })
}

export function useRecommendByCustomer() {
  return useMutation({
    mutationFn: ({ customerId, limit }: { customerId: string; limit?: number }) =>
      recommendByCustomer(customerId, limit),
    onError: (error: Error) =>
      toast.error('Falha ao buscar recomendações', { description: error.message }),
  })
}

