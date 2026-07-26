import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import {
  createIntegration,
  createBrandArchetypeProfile,
  deleteBrandArchetypeProfile,
  deleteIntegration,
  getBrandArchetypeProfiles,
  getCompanies,
  getIntegrations,
  updateBrandArchetypeProfile,
  updateIntegration,
} from '@/lib/api'
import type {
  BrandArchetypeProfileCreateInput,
  BrandArchetypeProfileUpdateInput,
  IntegrationCreateInput,
  IntegrationUpdateInput,
} from '@/types/api'

export const catalogKeys = {
  companies: ['catalog', 'companies'] as const,
  integrations: ['catalog', 'integrations'] as const,
  brandArchetypeProfiles: ['catalog', 'brand-archetype-profiles'] as const,
}

export function useCompanies() {
  return useQuery({ queryKey: catalogKeys.companies, queryFn: getCompanies })
}

export function useIntegrations() {
  return useQuery({ queryKey: catalogKeys.integrations, queryFn: getIntegrations })
}

export function useCreateIntegration() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data: IntegrationCreateInput) => createIntegration(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: catalogKeys.integrations })
      toast.success('Integração criada')
    },
    onError: (error: Error) =>
      toast.error('Falha ao criar integração', { description: error.message }),
  })
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

export function useBrandArchetypeProfiles() {
  return useQuery({
    queryKey: catalogKeys.brandArchetypeProfiles,
    queryFn: getBrandArchetypeProfiles,
  })
}

export function useCreateBrandArchetypeProfile() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data: BrandArchetypeProfileCreateInput) => createBrandArchetypeProfile(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: catalogKeys.brandArchetypeProfiles })
      toast.success('Arquétipo de marca criado')
    },
    onError: (error: Error) =>
      toast.error('Falha ao criar arquétipo de marca', { description: error.message }),
  })
}

export function useUpdateBrandArchetypeProfile() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: BrandArchetypeProfileUpdateInput }) =>
      updateBrandArchetypeProfile(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: catalogKeys.brandArchetypeProfiles })
      toast.success('Arquétipo de marca atualizado')
    },
    onError: (error: Error) =>
      toast.error('Falha ao atualizar arquétipo de marca', { description: error.message }),
  })
}

export function useDeleteBrandArchetypeProfile() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => deleteBrandArchetypeProfile(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: catalogKeys.brandArchetypeProfiles })
      toast.success('Arquétipo de marca removido')
    },
    onError: (error: Error) =>
      toast.error('Falha ao remover arquétipo de marca', { description: error.message }),
  })
}
