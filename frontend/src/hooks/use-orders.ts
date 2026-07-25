import { useQuery } from '@tanstack/react-query'
import { getOrderFilters, getOrders } from '@/lib/api'
import type { OrderFilterParams } from '@/types/api'

function stableFilters(filters: OrderFilterParams) {
  return Object.fromEntries(
    Object.entries(filters)
      .filter(([, values]) => values.length > 0)
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([key, values]) => [key, [...values].sort()]),
  )
}

export const orderKeys = {
  list: (filters: OrderFilterParams, limit: number, offset: number) =>
    ['orders', 'list', stableFilters(filters), limit, offset] as const,
  filters: (filters: OrderFilterParams) => ['orders', 'filters', stableFilters(filters)] as const,
}

export function useOrders(filters: OrderFilterParams, limit = 50, offset = 0) {
  return useQuery({
    queryKey: orderKeys.list(filters, limit, offset),
    queryFn: () => getOrders(filters, limit, offset),
  })
}

export function useOrderFilters(filters: OrderFilterParams) {
  return useQuery({
    queryKey: orderKeys.filters(filters),
    queryFn: () => getOrderFilters(filters),
  })
}
