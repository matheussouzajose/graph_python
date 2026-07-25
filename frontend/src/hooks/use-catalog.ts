import { useQuery } from '@tanstack/react-query'
import { getCompanies, getIntegrations } from '@/lib/api'

export function useCompanies() {
  return useQuery({ queryKey: ['catalog', 'companies'], queryFn: getCompanies })
}

export function useIntegrations() {
  return useQuery({ queryKey: ['catalog', 'integrations'], queryFn: getIntegrations })
}
