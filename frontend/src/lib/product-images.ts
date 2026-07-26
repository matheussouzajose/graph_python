import type { Product } from '@/types/api'

export type ProductImage = {
  url: string
  fallback: string | null
}

/** All photos for a product (every angle/variation in `product.media`), not
 * just the single `image_url` the API picks as the "main" one. */
export function productImages(product: Product): ProductImage[] {
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

export function objectValue(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {}
}

export function stringValue(value: unknown): string | null {
  return typeof value === 'string' && value ? value : null
}
