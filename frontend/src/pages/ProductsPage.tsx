import { useMemo, useState } from 'react'
import type { ColumnDef } from '@tanstack/react-table'
import { Loader2, Search, TrendingUp } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Button } from '@/components/ui/button'
import { DataTable } from '@/components/shared/DataTable'
import { ProductCombobox } from '@/components/shared/ProductCombobox'
import { RecommendationResultsTable } from '@/components/shared/RecommendationResultsTable'
import {
  useBoughtTogether,
  useTopPageRankProducts,
  useTopRevenueProducts,
  useTopSellingProducts,
} from '@/hooks/use-dashboard'
import { useRecommendByProduct } from '@/hooks/use-actions'
import { formatCurrency, formatDecimal, formatNumber } from '@/lib/format'
import type {
  BoughtTogetherPair,
  TopPageRankProduct,
  TopRevenueProduct,
  TopSellingProduct,
} from '@/types/api'

const sellingColumns: ColumnDef<TopSellingProduct, any>[] = [
  { accessorKey: 'product_name', header: 'Produto' },
  { accessorKey: 'product_code', header: 'Código' },
  {
    accessorKey: 'quantity_sold',
    header: 'Qtd. vendida',
    cell: ({ getValue }) => formatNumber(getValue<number>()),
  },
]

const revenueColumns: ColumnDef<TopRevenueProduct, any>[] = [
  { accessorKey: 'product_name', header: 'Produto' },
  { accessorKey: 'product_code', header: 'Código' },
  {
    accessorKey: 'revenue',
    header: 'Faturamento',
    cell: ({ getValue }) => formatCurrency(getValue<number>()),
  },
]

const pagerankColumns: ColumnDef<TopPageRankProduct, any>[] = [
  { accessorKey: 'product_name', header: 'Produto' },
  { accessorKey: 'product_code', header: 'Código' },
  {
    accessorKey: 'pagerank',
    header: 'PageRank',
    cell: ({ getValue }) => formatDecimal(getValue<number>(), 4),
  },
]

const boughtTogetherColumns: ColumnDef<BoughtTogetherPair, any>[] = [
  { accessorKey: 'product_name', header: 'Produto' },
  { accessorKey: 'related_product_name', header: 'Comprado com' },
  {
    accessorKey: 'support_count',
    header: 'Suporte',
    cell: ({ getValue }) => formatNumber(getValue<number>()),
  },
  {
    accessorKey: 'confidence',
    header: 'Confiança',
    cell: ({ getValue }) => formatDecimal(getValue<number>(), 2),
  },
  {
    accessorKey: 'lift',
    header: 'Lift',
    cell: ({ getValue }) => formatDecimal(getValue<number>(), 2),
  },
]

export function ProductsPage() {
  const topSelling = useTopSellingProducts(20)
  const topRevenue = useTopRevenueProducts(20)
  const topPagerank = useTopPageRankProducts(20)
  const boughtTogether = useBoughtTogether(undefined, 20)

  const [selectedProduct, setSelectedProduct] = useState<string | null>(null)
  const recommend = useRecommendByProduct()

  const productOptions = useMemo(() => {
    const seen = new Map<string, { product_id: string; product_name: string | null; product_code: string | null }>()
    for (const product of topSelling.data ?? []) seen.set(product.product_id, product)
    for (const product of topRevenue.data ?? []) seen.set(product.product_id, product)
    for (const product of topPagerank.data ?? []) seen.set(product.product_id, product)
    return Array.from(seen.values())
  }, [topSelling.data, topRevenue.data, topPagerank.data])

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">Ranking de produtos</CardTitle>
        </CardHeader>
        <CardContent>
          <Tabs defaultValue="selling">
            <TabsList>
              <TabsTrigger value="selling">Mais vendidos</TabsTrigger>
              <TabsTrigger value="revenue">Maior faturamento</TabsTrigger>
              <TabsTrigger value="pagerank">Mais importantes</TabsTrigger>
              <TabsTrigger value="bought-together">Comprados juntos</TabsTrigger>
            </TabsList>
            <TabsContent value="selling" className="mt-4">
              <DataTable
                columns={sellingColumns}
                data={topSelling.data}
                loading={topSelling.isLoading}
                emptyTitle="Nenhum produto vendido ainda"
                emptyDescription="Sincronize pedidos e projete-os no grafo para ver o ranking aqui."
                getRowId={(row) => row.product_id}
              />
            </TabsContent>
            <TabsContent value="revenue" className="mt-4">
              <DataTable
                columns={revenueColumns}
                data={topRevenue.data}
                loading={topRevenue.isLoading}
                emptyTitle="Nenhum faturamento calculado ainda"
                getRowId={(row) => row.product_id}
              />
            </TabsContent>
            <TabsContent value="pagerank" className="mt-4">
              <DataTable
                columns={pagerankColumns}
                data={topPagerank.data}
                loading={topPagerank.isLoading}
                emptyTitle="PageRank ainda não calculado"
                emptyDescription='Rode "Rodar algoritmos" na Home para calcular o PageRank de produtos.'
                getRowId={(row) => row.product_id}
              />
            </TabsContent>
            <TabsContent value="bought-together" className="mt-4">
              <DataTable
                columns={boughtTogetherColumns}
                data={boughtTogether.data}
                loading={boughtTogether.isLoading}
                emptyTitle="Nenhuma regra de associação calculada ainda"
                emptyDescription='Rode "Rodar algoritmos" na Home para gerar as regras de produtos comprados juntos.'
                getRowId={(row) => `${row.product_id}-${row.related_product_id}`}
              />
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">Recomendações por produto</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap items-center gap-2">
            <ProductCombobox
              products={productOptions}
              value={selectedProduct}
              onChange={setSelectedProduct}
              loading={topSelling.isLoading}
            />
            <Button
              disabled={!selectedProduct || recommend.isPending}
              onClick={() =>
                selectedProduct && recommend.mutate({ productId: selectedProduct, limit: 10 })
              }
            >
              {recommend.isPending ? (
                <Loader2 className="size-4 animate-spin" />
              ) : (
                <Search className="size-4" />
              )}
              Ver recomendações
            </Button>
          </div>
          {recommend.data ? (
            <RecommendationResultsTable results={recommend.data} loading={recommend.isPending} />
          ) : (
            <div className="flex items-center gap-2 rounded-md border border-dashed p-4 text-sm text-muted-foreground">
              <TrendingUp className="size-4" />
              Escolha um produto e clique em "Ver recomendações".
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
