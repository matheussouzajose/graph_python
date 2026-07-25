import { useState } from 'react'
import { Loader2, Search } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Button } from '@/components/ui/button'
import { ProductCombobox } from '@/components/shared/ProductCombobox'
import { CustomerCombobox } from '@/components/shared/CustomerCombobox'
import { RecommendationResultsTable } from '@/components/shared/RecommendationResultsTable'
import { SegmentBadge } from '@/components/shared/SegmentBadge'
import { useCustomers, useTopSellingProducts } from '@/hooks/use-dashboard'
import { useRecommendByCustomer, useRecommendByProduct } from '@/hooks/use-actions'

export function RecommendationsPage() {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium">Central de recomendações</CardTitle>
      </CardHeader>
      <CardContent>
        <Tabs defaultValue="product">
          <TabsList>
            <TabsTrigger value="product">Por produto</TabsTrigger>
            <TabsTrigger value="customer">Por cliente</TabsTrigger>
          </TabsList>
          <TabsContent value="product" className="mt-4">
            <ByProductPanel />
          </TabsContent>
          <TabsContent value="customer" className="mt-4">
            <ByCustomerPanel />
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  )
}

function ByProductPanel() {
  const products = useTopSellingProducts(50)
  const [selectedProduct, setSelectedProduct] = useState<string | null>(null)
  const recommend = useRecommendByProduct()

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <ProductCombobox
          products={products.data ?? []}
          value={selectedProduct}
          onChange={setSelectedProduct}
          loading={products.isLoading}
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
          Recomendar
        </Button>
      </div>
      {recommend.data ? (
        <RecommendationResultsTable results={recommend.data} loading={recommend.isPending} />
      ) : (
        <p className="text-sm text-muted-foreground">
          Escolha um produto e clique em "Recomendar" para ver produtos relacionados por
          similaridade e coocorrência.
        </p>
      )}
    </div>
  )
}

function ByCustomerPanel() {
  const customers = useCustomers(undefined, 100, 0)
  const [selectedCustomer, setSelectedCustomer] = useState<string | null>(null)
  const recommend = useRecommendByCustomer()

  const selected = (customers.data ?? []).find((c) => c.customer_id === selectedCustomer)

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <CustomerCombobox
          customers={customers.data ?? []}
          value={selectedCustomer}
          onChange={setSelectedCustomer}
          loading={customers.isLoading}
        />
        <Button
          disabled={!selectedCustomer || recommend.isPending}
          onClick={() =>
            selectedCustomer && recommend.mutate({ customerId: selectedCustomer, limit: 10 })
          }
        >
          {recommend.isPending ? (
            <Loader2 className="size-4 animate-spin" />
          ) : (
            <Search className="size-4" />
          )}
          Recomendar
        </Button>
        {selected ? <SegmentBadge segment={selected.rfm_segment} /> : null}
      </div>
      {recommend.data ? (
        <RecommendationResultsTable results={recommend.data} loading={recommend.isPending} />
      ) : (
        <p className="text-sm text-muted-foreground">
          Escolha um cliente e clique em "Recomendar" para ver produtos baseados no histórico de
          compras e no segmento RFM.
        </p>
      )}
    </div>
  )
}
