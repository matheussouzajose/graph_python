import { useQuery } from '@tanstack/react-query'
import {
  getBoughtTogether,
  getCustomer,
  getCustomers,
  getOverview,
  getRfmSummary,
  getSyncStatus,
  getTopPageRankProducts,
  getTopRevenueProducts,
  getTopSellingProducts,
} from '@/lib/api'
import type { SyncStatus } from '@/types/api'

export const dashboardKeys = {
  overview: ['dashboard', 'overview'] as const,
  syncStatus: ['dashboard', 'sync-status'] as const,
  topSelling: (limit: number) => ['dashboard', 'products', 'top-selling', limit] as const,
  topRevenue: (limit: number) => ['dashboard', 'products', 'top-revenue', limit] as const,
  topPagerank: (limit: number) => ['dashboard', 'products', 'top-pagerank', limit] as const,
  boughtTogether: (productId: string | undefined, limit: number) =>
    ['dashboard', 'products', 'bought-together', productId ?? null, limit] as const,
  rfmSummary: ['dashboard', 'customers', 'rfm-summary'] as const,
  customers: (segment: string | undefined, limit: number, offset: number) =>
    ['dashboard', 'customers', segment ?? null, limit, offset] as const,
  customer: (customerId: string | undefined) => ['dashboard', 'customer', customerId] as const,
}

export function useOverview() {
  return useQuery({ queryKey: dashboardKeys.overview, queryFn: getOverview })
}

export function useSyncStatus() {
  return useQuery({
    queryKey: dashboardKeys.syncStatus,
    queryFn: getSyncStatus,
    // Enquanto alguma integração está "running", há um sync em andamento em
    // outro processo (worker/consumer) — poll a cada 5s pra refletir sem
    // precisar de refresh manual. Some running -> volta a não pollar.
    refetchInterval: (query) => {
      const data = query.state.data as SyncStatus | undefined
      const hasRunning = data?.integrations.some((integration) => integration.status === 'running')
      return hasRunning ? 5000 : false
    },
  })
}

export function useTopSellingProducts(limit = 10) {
  return useQuery({
    queryKey: dashboardKeys.topSelling(limit),
    queryFn: () => getTopSellingProducts(limit),
  })
}

export function useTopRevenueProducts(limit = 10) {
  return useQuery({
    queryKey: dashboardKeys.topRevenue(limit),
    queryFn: () => getTopRevenueProducts(limit),
  })
}

export function useTopPageRankProducts(limit = 10) {
  return useQuery({
    queryKey: dashboardKeys.topPagerank(limit),
    queryFn: () => getTopPageRankProducts(limit),
  })
}

export function useBoughtTogether(productId?: string, limit = 10) {
  return useQuery({
    queryKey: dashboardKeys.boughtTogether(productId, limit),
    queryFn: () => getBoughtTogether(productId, limit),
  })
}

export function useRfmSummary() {
  return useQuery({ queryKey: dashboardKeys.rfmSummary, queryFn: getRfmSummary })
}

export function useCustomers(segment?: string, limit = 50, offset = 0) {
  return useQuery({
    queryKey: dashboardKeys.customers(segment, limit, offset),
    queryFn: () => getCustomers(segment, limit, offset),
  })
}

export function useCustomer(customerId: string | undefined) {
  return useQuery({
    queryKey: dashboardKeys.customer(customerId),
    queryFn: () => getCustomer(customerId as string),
    enabled: Boolean(customerId),
  })
}
