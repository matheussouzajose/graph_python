import { useState } from 'react'
import { ArrowRight, Loader2, Search, Sparkles, Target } from 'lucide-react'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Button } from '@/components/ui/button'
import { SectionCard } from '@/components/shared/SectionCard'
import { ProductCombobox } from '@/components/shared/ProductCombobox'
import { CustomerCombobox } from '@/components/shared/CustomerCombobox'
import { RecommendationResultsTable } from '@/components/shared/RecommendationResultsTable'
import { SegmentBadge } from '@/components/shared/SegmentBadge'
import { useCustomers, useTopSellingProducts } from '@/hooks/use-dashboard'
import { useRecommendByCustomer, useRecommendByProduct } from '@/hooks/use-actions'

export function RecommendationsPage() {
  return (
    <div className="space-y-6">
      <section className="dark-panel relative overflow-hidden rounded-3xl p-5 sm:p-6">
        <div className="surface-glow absolute right-8 top-4 h-44 w-44 rounded-full bg-amber-300/18 blur-3xl" />
        <div className="relative grid gap-5 lg:grid-cols-[1fr_360px] lg:items-center">
          <div>
            <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/8 px-3 py-1.5 text-xs text-amber-100">
              <Target className="size-3.5" />
              Máquina de próxima oferta
            </div>
            <h2 className="mt-4 max-w-2xl text-3xl font-semibold tracking-normal">
              Saia de uma entidade e chegue em uma lista pronta para vender.
            </h2>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-white/55">
              Escolha produto ou cliente, gere recomendações e use o resultado como insumo para
              campanha, atendimento ou priorização comercial.
            </p>
          </div>
          <div className="rounded-2xl border border-white/10 bg-white/[0.075] p-4">
            <div className="flex items-center gap-3">
              <div className="flex size-11 items-center justify-center rounded-2xl bg-amber-300 text-slate-950">
                <ArrowRight className="size-5" />
              </div>
              <div>
                <p className="text-sm font-semibold">Fluxo guiado</p>
                <p className="text-xs text-white/45">Contexto → recomendação → ação</p>
              </div>
            </div>
            <div className="mt-4 h-1.5 overflow-hidden rounded-full bg-white/10">
              <div className="progress-breathe h-full w-[74%] rounded-full bg-amber-300" />
            </div>
          </div>
        </div>
      </section>

      <SectionCard title="Central de recomendações" icon={Sparkles}>
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
      </SectionCard>
    </div>
  )
}

function ByProductPanel() {
  const products = useTopSellingProducts(50)
  const [selectedProduct, setSelectedProduct] = useState<string | null>(null)
  const recommend = useRecommendByProduct()

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2 rounded-lg border bg-muted/35 p-3">
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
        <div className="rounded-lg border border-dashed bg-card p-4">
          <p className="text-sm font-medium">Nenhuma recomendação gerada</p>
          <p className="mt-1 text-sm text-muted-foreground">
            Escolha um produto para ver itens relacionados por similaridade e coocorrência.
          </p>
        </div>
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
      <div className="flex flex-wrap items-center gap-2 rounded-lg border bg-muted/35 p-3">
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
        <div className="rounded-lg border border-dashed bg-card p-4">
          <p className="text-sm font-medium">Nenhuma recomendação gerada</p>
          <p className="mt-1 text-sm text-muted-foreground">
            Escolha um cliente para ver produtos baseados no histórico de compras e no segmento RFM.
          </p>
        </div>
      )}
    </div>
  )
}
