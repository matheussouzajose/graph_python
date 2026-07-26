import { useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import {
  Boxes,
  ChevronFirst,
  ChevronLast,
  ChevronLeft,
  ChevronRight,
  ExternalLink,
  ImageOff,
  Package,
  Palette,
  Ruler,
  Search,
  SlidersHorizontal,
  Tag,
} from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet'
import { EmptyState } from '@/components/shared/EmptyState'
import { PageHeader } from '@/components/shared/PageHeader'
import { RelativeTime } from '@/components/shared/RelativeTime'
import { useProducts } from '@/hooks/use-products'
import { formatCurrency, formatNumber } from '@/lib/format'
import type { Product } from '@/types/api'

const PAGE_SIZE_OPTIONS = [24, 48, 96] as const

export function ProductCatalogPage() {
  const [search, setSearch] = useState('')
  const [activeFilter, setActiveFilter] = useState<string>('all')
  const [pageSize, setPageSize] = useState<number>(48)
  const [page, setPage] = useState(1)
  const [selectedProduct, setSelectedProduct] = useState<Product | null>(null)
  const active = activeFilter === 'all' ? null : activeFilter === 'active'
  const offset = (page - 1) * pageSize
  const products = useProducts(search, active, pageSize, offset)
  const total = products.data?.total ?? 0
  const totalPages = Math.max(1, Math.ceil(total / pageSize))
  const items = useMemo(() => products.data?.items ?? [], [products.data?.items])
  const currentPage = Math.min(page, totalPages)
  const firstItem = total === 0 ? 0 : offset + 1
  const lastItem = Math.min(offset + items.length, total)

  const summary = useMemo(() => {
    const activeCount = items.filter((product) => product.active).length
    const stockCount = items.reduce((sum, product) => sum + productStock(product), 0)
    const promoCount = items.filter((product) => product.promotion).length
    return { activeCount, stockCount, promoCount }
  }, [items])

  useEffect(() => {
    if (!products.data || page <= totalPages) return
    setPage(totalPages)
  }, [page, products.data, totalPages])

  function updateSearch(value: string) {
    setSearch(value)
    setPage(1)
  }

  function updateActiveFilter(value: string) {
    setActiveFilter(value)
    setPage(1)
  }

  function updatePageSize(value: string) {
    setPageSize(Number(value))
    setPage(1)
  }

  return (
    <div className="space-y-5">
      <PageHeader
        title="Catálogo ERP"
        description="Produtos sincronizados diretamente do ERP Vesti, separados das análises de vendas."
        icon={Package}
      />

      <div className="space-y-4 rounded-xl border bg-card p-4 shadow-sm">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0">
            <h2 className="flex items-center gap-2 text-sm font-semibold">
              <Package className="size-4 text-primary" />
              Produtos integrados
            </h2>
            <p className="mt-1 text-xs text-muted-foreground">
              Consulte o catálogo operacional com imagens, status, marca, categorias e estoque.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant="outline">{formatNumber(total)} produto(s)</Badge>
            {products.isFetching && !products.isLoading ? (
              <Badge variant="secondary">Atualizando</Badge>
            ) : null}
          </div>
        </div>

        <div className="grid gap-3 xl:grid-cols-[minmax(280px,1fr)_auto_auto]">
          <div className="relative">
            <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              value={search}
              onChange={(event) => updateSearch(event.target.value)}
              placeholder="Buscar por nome, código ou integração"
              className="h-10 pl-9"
            />
          </div>

          <div className="flex rounded-lg border bg-background p-1">
            {[
              ['all', 'Todos'],
              ['active', 'Ativos'],
              ['inactive', 'Inativos'],
            ].map(([value, label]) => (
              <Button
                key={value}
                type="button"
                variant={activeFilter === value ? 'secondary' : 'ghost'}
                size="sm"
                className="h-7"
                onClick={() => updateActiveFilter(value)}
              >
                {label}
              </Button>
            ))}
          </div>

          <Select value={String(pageSize)} onValueChange={updatePageSize}>
            <SelectTrigger className="h-10 w-full xl:w-[150px]">
              <SlidersHorizontal className="size-4 text-muted-foreground" />
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {PAGE_SIZE_OPTIONS.map((value) => (
                <SelectItem key={value} value={String(value)}>
                  {value} por página
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="grid gap-3 sm:grid-cols-3">
          <CatalogMetric label="Ativos nesta página" value={formatNumber(summary.activeCount)} />
          <CatalogMetric label="Em promoção nesta página" value={formatNumber(summary.promoCount)} />
          <CatalogMetric label="Estoque nesta página" value={formatNumber(summary.stockCount)} />
        </div>

        {products.isLoading ? (
          <ProductGridSkeleton pageSize={pageSize} />
        ) : items.length ? (
          <>
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4">
              {items.map((product) => (
                <ProductCard
                  key={product.id}
                  product={product}
                  onClick={() => setSelectedProduct(product)}
                />
              ))}
            </div>
            <CatalogPagination
              page={currentPage}
              totalPages={totalPages}
              firstItem={firstItem}
              lastItem={lastItem}
              total={total}
              fetching={products.isFetching}
              onPageChange={setPage}
            />
          </>
        ) : (
          <div className="flex min-h-[20rem] items-center justify-center rounded-lg border border-dashed">
            <EmptyState
              icon={Package}
              title={
                search || activeFilter !== 'all'
                  ? 'Nenhum produto encontrado'
                  : 'Nenhum produto integrado'
              }
              description={
                search || activeFilter !== 'all'
                  ? 'Ajuste a busca ou o filtro de status para ampliar os resultados.'
                  : 'Sincronize a integração Vesti com o recurso Produtos habilitado para preencher o catálogo.'
              }
            />
          </div>
        )}
      </div>

      <ProductDetailSheet product={selectedProduct} onClose={() => setSelectedProduct(null)} />
    </div>
  )
}

function CatalogMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border bg-muted/25 px-3 py-2">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="mt-0.5 text-sm font-semibold">{value}</p>
    </div>
  )
}

function CatalogPagination({
  page,
  totalPages,
  firstItem,
  lastItem,
  total,
  fetching,
  onPageChange,
}: {
  page: number
  totalPages: number
  firstItem: number
  lastItem: number
  total: number
  fetching: boolean
  onPageChange: (page: number) => void
}) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border bg-background px-3 py-2.5">
      <p className="text-sm text-muted-foreground">
        Exibindo {formatNumber(firstItem)}-{formatNumber(lastItem)} de {formatNumber(total)}
      </p>
      <div className="flex items-center gap-1.5">
        <Button
          type="button"
          variant="outline"
          size="icon-sm"
          disabled={page === 1 || fetching}
          onClick={() => onPageChange(1)}
        >
          <ChevronFirst className="size-4" />
        </Button>
        <Button
          type="button"
          variant="outline"
          size="icon-sm"
          disabled={page === 1 || fetching}
          onClick={() => onPageChange(Math.max(1, page - 1))}
        >
          <ChevronLeft className="size-4" />
        </Button>
        <span className="min-w-24 text-center text-sm font-medium">
          {page} / {totalPages}
        </span>
        <Button
          type="button"
          variant="outline"
          size="icon-sm"
          disabled={page === totalPages || fetching}
          onClick={() => onPageChange(Math.min(totalPages, page + 1))}
        >
          <ChevronRight className="size-4" />
        </Button>
        <Button
          type="button"
          variant="outline"
          size="icon-sm"
          disabled={page === totalPages || fetching}
          onClick={() => onPageChange(totalPages)}
        >
          <ChevronLast className="size-4" />
        </Button>
      </div>
    </div>
  )
}

function ProductCard({ product, onClick }: { product: Product; onClick: () => void }) {
  const imageUrl = product.image_url ?? product.image_fallback_url
  const brand = typeof product.brand.name === 'string' ? product.brand.name : null
  const categories = categoryNames(product.categories).slice(0, 3)
  const stock = productStock(product)
  const price = product.promotion ? product.price_promotional : product.price

  return (
    <button
      type="button"
      onClick={onClick}
      className="group grid min-w-0 cursor-pointer grid-cols-[96px_1fr] gap-3 rounded-lg border bg-card p-3 text-left shadow-sm transition hover:-translate-y-0.5 hover:border-primary/25 hover:shadow-md focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 focus-visible:outline-none"
    >
      <div className="flex aspect-[3/4] w-24 items-center justify-center overflow-hidden rounded-md border bg-muted">
        {imageUrl ? (
          <img
            src={imageUrl}
            alt={product.name ?? 'Produto'}
            className="h-full w-full object-cover transition-transform group-hover:scale-[1.03]"
            loading="lazy"
            onError={(event) => {
              if (product.image_fallback_url && event.currentTarget.src !== product.image_fallback_url) {
                event.currentTarget.src = product.image_fallback_url
              }
            }}
          />
        ) : (
          <ImageOff className="size-5 text-muted-foreground" />
        )}
      </div>
      <div className="min-w-0 space-y-2">
        <div className="space-y-1">
          <h3 className="line-clamp-2 text-sm font-semibold" title={product.name ?? undefined}>
            {product.name ?? 'Produto sem nome'}
          </h3>
          <p className="truncate font-mono text-xs text-muted-foreground">
            {product.code ?? product.integration_product_id ?? product.external_product_id}
          </p>
        </div>
        <div className="flex flex-wrap gap-1.5">
          <Badge
            variant="outline"
            className={
              product.active
                ? 'border-emerald-200 bg-emerald-50 text-emerald-700'
                : 'border-slate-200 bg-slate-100 text-slate-600'
            }
          >
            {product.active ? 'Ativo' : 'Inativo'}
          </Badge>
          {brand ? <Badge variant="outline">{brand}</Badge> : null}
          {product.promotion ? <Badge variant="outline">Promoção</Badge> : null}
        </div>
        <div className="grid grid-cols-2 gap-2 text-xs">
          <Info label="Preço" value={price ? formatCurrency(price) : '-'} />
          <Info label="Estoque" value={formatNumber(stock)} />
        </div>
        {categories.length ? (
          <div className="flex flex-wrap gap-1">
            {categories.map((category) => (
              <Badge key={category} variant="secondary">
                {category}
              </Badge>
            ))}
          </div>
        ) : null}
        <p className="text-xs text-muted-foreground">
          Atualizado <RelativeTime value={product.external_updated_at ?? product.updated_at} />
        </p>
      </div>
    </button>
  )
}

function ProductDetailSheet({
  product,
  onClose,
}: {
  product: Product | null
  onClose: () => void
}) {
  const [selectedImage, setSelectedImage] = useState(0)
  const images = useMemo(() => (product ? productImages(product) : []), [product])
  const stock = product ? productStock(product) : 0
  const brand = product && typeof product.brand.name === 'string' ? product.brand.name : null
  const categories = product ? categoryNames(product.categories) : []
  const price = product?.promotion ? product.price_promotional : product?.price
  const mainImage = images[selectedImage] ?? images[0]

  function close() {
    setSelectedImage(0)
    onClose()
  }

  return (
    <Sheet open={Boolean(product)} onOpenChange={(open) => !open && close()}>
      <SheetContent className="overflow-y-auto data-[side=right]:w-full data-[side=right]:sm:max-w-none data-[side=right]:xl:w-[78vw]">
        {product ? (
          <>
            <SheetHeader className="border-b pr-14">
              <SheetTitle className="line-clamp-2 text-lg">{product.name ?? 'Produto'}</SheetTitle>
              <SheetDescription className="flex flex-wrap items-center gap-2">
                <span className="font-mono">
                  {product.code ?? product.integration_product_id ?? product.external_product_id}
                </span>
                {brand ? <span>{brand}</span> : null}
              </SheetDescription>
            </SheetHeader>

            <div className="grid gap-5 px-4 pb-6 lg:grid-cols-[minmax(320px,0.95fr)_1.25fr]">
              <section className="space-y-3">
                <div className="flex aspect-[4/5] min-h-[360px] items-center justify-center overflow-hidden rounded-lg border bg-muted">
                  {mainImage ? (
                    <img
                      src={mainImage.url}
                      alt={product.name ?? 'Produto'}
                      className="h-full w-full object-contain"
                      onError={(event) => {
                        if (
                          mainImage.fallback &&
                          event.currentTarget.src !== mainImage.fallback
                        ) {
                          event.currentTarget.src = mainImage.fallback
                        }
                      }}
                    />
                  ) : (
                    <div className="flex flex-col items-center gap-2 text-muted-foreground">
                      <ImageOff className="size-7" />
                      <span className="text-sm">Sem imagem</span>
                    </div>
                  )}
                </div>
                {images.length > 1 ? (
                  <div className="grid grid-cols-5 gap-2 sm:grid-cols-6 lg:grid-cols-5 xl:grid-cols-6">
                    {images.map((image, index) => (
                      <button
                        key={`${image.url}-${index}`}
                        type="button"
                        onClick={() => setSelectedImage(index)}
                        className={[
                          'flex aspect-square items-center justify-center overflow-hidden rounded-md border bg-muted transition-colors',
                          selectedImage === index
                            ? 'border-primary ring-2 ring-primary/20'
                            : 'hover:border-foreground/30',
                        ].join(' ')}
                      >
                        <img
                          src={image.url}
                          alt={`${product.name ?? 'Produto'} ${index + 1}`}
                          className="h-full w-full object-cover"
                          loading="lazy"
                          onError={(event) => {
                            if (
                              image.fallback &&
                              event.currentTarget.src !== image.fallback
                            ) {
                              event.currentTarget.src = image.fallback
                            }
                          }}
                        />
                      </button>
                    ))}
                  </div>
                ) : null}
              </section>

              <section className="min-w-0 space-y-4">
                <div className="flex flex-wrap gap-1.5">
                  <Badge
                    variant="outline"
                    className={
                      product.active
                        ? 'border-emerald-200 bg-emerald-50 text-emerald-700'
                        : 'border-slate-200 bg-slate-100 text-slate-600'
                    }
                  >
                    {product.active ? 'Ativo' : 'Inativo'}
                  </Badge>
                  {product.promotion ? <Badge variant="outline">Promoção</Badge> : null}
                  {brand ? <Badge variant="outline">{brand}</Badge> : null}
                  {product.url ? (
                    <a href={product.url} target="_blank" rel="noreferrer">
                      <Badge variant="outline" className="gap-1">
                        <ExternalLink className="size-3" />
                        URL
                      </Badge>
                    </a>
                  ) : null}
                </div>

                <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                  <Metric icon={Tag} label="Preço" value={price ? formatCurrency(price) : '-'} />
                  <Metric icon={Boxes} label="Estoque" value={formatNumber(stock)} />
                  <Metric
                    icon={Palette}
                    label="Cores"
                    value={formatNumber(product.colors.length)}
                  />
                  <Metric icon={Ruler} label="Tamanhos" value={formatNumber(product.sizes.length)} />
                </div>

                <DetailSection title="Descrição">
                  <p className="whitespace-pre-wrap text-sm leading-6 text-muted-foreground">
                    {product.full_description || product.description || 'Sem descrição.'}
                  </p>
                  {product.composition ? (
                    <p className="text-sm">
                      <span className="font-medium text-muted-foreground">Composição: </span>
                      {product.composition}
                    </p>
                  ) : null}
                </DetailSection>

                {categories.length ? (
                  <DetailSection title="Categorias">
                    <div className="flex flex-wrap gap-1.5">
                      {categories.map((category) => (
                        <Badge key={category} variant="secondary">
                          {category}
                        </Badge>
                      ))}
                    </div>
                  </DetailSection>
                ) : null}

                <DetailSection title="Estoque por variação">
                  {product.stocks.length ? (
                    <div className="overflow-x-auto rounded-lg border">
                      <table className="w-full text-sm">
                        <thead className="bg-muted/60 text-xs text-muted-foreground">
                          <tr>
                            <th className="px-3 py-2 text-left font-medium">SKU</th>
                            <th className="px-3 py-2 text-left font-medium">Cor</th>
                            <th className="px-3 py-2 text-left font-medium">Tamanho</th>
                            <th className="px-3 py-2 text-right font-medium">Qtd.</th>
                          </tr>
                        </thead>
                        <tbody>
                          {product.stocks.map((stockItem, index) => (
                            <tr key={`${stockItem.sku ?? index}`} className="border-t">
                              <td className="px-3 py-2 font-mono text-xs">
                                {String(stockItem.sku ?? '-')}
                              </td>
                              <td className="px-3 py-2">
                                {colorName(product, stockItem.color_id)}
                              </td>
                              <td className="px-3 py-2">{sizeName(product, stockItem.size_id)}</td>
                              <td className="px-3 py-2 text-right">
                                {formatNumber(Number(stockItem.quantity ?? 0))}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  ) : (
                    <p className="text-sm text-muted-foreground">Sem estoque informado.</p>
                  )}
                </DetailSection>

                <DetailSection title="Dados ERP">
                  <div className="grid gap-2 text-sm sm:grid-cols-2">
                    <Detail label="ID ERP" value={product.external_product_id} mono />
                    <Detail label="Integration ID" value={product.integration_product_id} mono />
                    <Detail label="Slug" value={product.slug} />
                    <Detail
                      label="Criado no ERP"
                      value={formatDateValue(product.external_created_at)}
                    />
                    <Detail
                      label="Atualizado no ERP"
                      value={formatDateValue(product.external_updated_at)}
                    />
                    <Detail label="Release" value={formatDateValue(product.release_at)} />
                  </div>
                </DetailSection>
              </section>
            </div>
          </>
        ) : null}
      </SheetContent>
    </Sheet>
  )
}

function DetailSection({
  title,
  children,
}: {
  title: string
  children: ReactNode
}) {
  return (
    <section className="space-y-2 rounded-lg border bg-card p-3 shadow-sm">
      <h3 className="text-sm font-semibold">{title}</h3>
      {children}
    </section>
  )
}

function Metric({
  icon: Icon,
  label,
  value,
}: {
  icon: typeof Package
  label: string
  value: string
}) {
  return (
    <div className="min-w-0 rounded-lg border bg-card p-3 shadow-sm">
      <div className="flex items-center gap-2 text-xs font-medium text-muted-foreground">
        <Icon className="size-4" />
        {label}
      </div>
      <p className="mt-1 truncate text-lg font-semibold">{value}</p>
    </div>
  )
}

function Detail({
  label,
  value,
  mono,
}: {
  label: string
  value: string | null
  mono?: boolean
}) {
  return (
    <div className="min-w-0 rounded-md bg-muted/40 px-2.5 py-2">
      <p className="text-xs font-medium text-muted-foreground">{label}</p>
      <p className={['mt-0.5 truncate', mono ? 'font-mono text-xs' : ''].join(' ')}>
        {value || '-'}
      </p>
    </div>
  )
}

function Info({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0 rounded-md bg-muted/45 px-2 py-1">
      <p className="text-[11px] font-medium text-muted-foreground">{label}</p>
      <p className="truncate font-medium">{value}</p>
    </div>
  )
}

function ProductGridSkeleton({ pageSize }: { pageSize: number }) {
  const count = Math.min(pageSize, 12)
  return (
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4">
      {Array.from({ length: count }).map((_, index) => (
        <div key={index} className="grid grid-cols-[96px_1fr] gap-3 rounded-lg border bg-card p-3">
          <div className="aspect-[3/4] w-24 animate-pulse rounded-md bg-muted" />
          <div className="space-y-2">
            <div className="h-4 w-4/5 animate-pulse rounded bg-muted" />
            <div className="h-3 w-2/3 animate-pulse rounded bg-muted" />
            <div className="h-5 w-28 animate-pulse rounded bg-muted" />
            <div className="grid grid-cols-2 gap-2">
              <div className="h-10 animate-pulse rounded bg-muted" />
              <div className="h-10 animate-pulse rounded bg-muted" />
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}

function productStock(product: Product): number {
  return product.stocks.reduce((sum, stock) => {
    const quantity = Number(stock.quantity ?? 0)
    return sum + (Number.isFinite(quantity) ? quantity : 0)
  }, 0)
}

function categoryNames(categories: Record<string, unknown>[]): string[] {
  const names: string[] = []
  for (const category of categories) {
    if (typeof category.name === 'string') names.push(category.name)
    if (Array.isArray(category.children)) {
      names.push(...categoryNames(category.children as Record<string, unknown>[]))
    }
  }
  return names
}

type ProductImage = {
  url: string
  fallback: string | null
}

function productImages(product: Product): ProductImage[] {
  const images: ProductImage[] = []
  for (const item of product.media) {
    const normal = objectValue(item.normal)
    const zoom = objectValue(item.zoom)
    const url = stringValue(zoom.url) ?? stringValue(normal.url)
    const fallback = stringValue(zoom.fallback) ?? stringValue(normal.fallback)
    if (url) images.push({ url, fallback })
  }
  if (!images.length && product.image_url) {
    images.push({ url: product.image_url, fallback: product.image_fallback_url })
  }
  return dedupeImages(images)
}

function dedupeImages(images: ProductImage[]): ProductImage[] {
  const seen = new Set<string>()
  return images.filter((image) => {
    if (seen.has(image.url)) return false
    seen.add(image.url)
    return true
  })
}

function objectValue(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {}
}

function stringValue(value: unknown): string | null {
  return typeof value === 'string' && value ? value : null
}

function colorName(product: Product, colorId: unknown): string {
  const color = product.colors.find((item) => item.id === colorId)
  return stringValue(color?.name) ?? '-'
}

function sizeName(product: Product, sizeId: unknown): string {
  const size = product.sizes.find((item) => item.id === sizeId)
  return stringValue(size?.name) ?? '-'
}

function formatDateValue(value: string | null): string | null {
  if (!value) return null
  return new Intl.DateTimeFormat('pt-BR', {
    dateStyle: 'short',
    timeStyle: 'short',
  }).format(new Date(value))
}
