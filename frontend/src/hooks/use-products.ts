import { useQuery } from '@tanstack/react-query'
import { getProducts } from '@/lib/api'

export const productKeys = {
  list: (search: string, active: boolean | null, limit: number, offset: number) =>
    ['products', search, active, limit, offset] as const,
}

export function useProducts(search = '', active: boolean | null = null, limit = 48, offset = 0) {
  return useQuery({
    queryKey: productKeys.list(search, active, limit, offset),
    queryFn: () => getProducts(search, active, limit, offset),
  })
}
