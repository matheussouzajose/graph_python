import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { deleteIntegration, getCompanies, getIntegrations, updateIntegration } from '@/lib/api'
import type { IntegrationUpdateInput } from '@/types/api'

export const catalogKeys = {
  companies: ['catalog', 'companies'] as const,
  integrations: ['catalog', 'integrations'] as const,
}

export function useCompanies() {
  return useQuery({ queryKey: catalogKeys.companies, queryFn: getCompanies })
}

export function useIntegrations() {
  return useQuery({ queryKey: catalogKeys.integrations, queryFn: getIntegrations })
}

export function useUpdateIntegration() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: IntegrationUpdateInput }) =>
      updateIntegration(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: catalogKeys.integrations })
      toast.success('Integração atualizada')
    },
    onError: (error: Error) =>
      toast.error('Falha ao atualizar integração', { description: error.message }),
  })
}

export function useDeleteIntegration() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => deleteIntegration(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: catalogKeys.integrations })
      toast.success('Integração removida')
    },
    onError: (error: Error) =>
      toast.error('Falha ao remover integração', { description: error.message }),
  })
}
