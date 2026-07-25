import type {
  AskResponse,
  BoughtTogetherPair,
  Company,
  CustomerDetail,
  CustomerSummary,
  Integration,
  OracleStreamEvent,
  Overview,
  RecommendationResult,
  RfmSegmentSummary,
  SyncStatus,
  TopPageRankProduct,
  TopRevenueProduct,
  TopSellingProduct,
  TriggerResponse,
} from '@/types/api'

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api/v1'

export class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...init?.headers,
    },
  })

  if (!response.ok) {
    const body = await response.text()
    let message = body
    try {
      const parsed = JSON.parse(body)
      message = parsed?.error?.message ?? parsed?.detail ?? body
    } catch {
      // corpo não era JSON — usa o texto cru mesmo
    }
    throw new ApiError(response.status, message || `Erro ${response.status}`)
  }

  if (response.status === 204) {
    return undefined as T
  }
  return (await response.json()) as T
}

function qs(params: Record<string, string | number | boolean | null | undefined>): string {
  const search = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value !== null && value !== undefined && value !== '') {
      search.set(key, String(value))
    }
  }
  const query = search.toString()
  return query ? `?${query}` : ''
}

// Dashboard
export const getOverview = () => request<Overview>('/dashboard/overview')

export const getTopSellingProducts = (limit = 10) =>
  request<TopSellingProduct[]>(`/dashboard/products/top-selling${qs({ limit })}`)

export const getTopRevenueProducts = (limit = 10) =>
  request<TopRevenueProduct[]>(`/dashboard/products/top-revenue${qs({ limit })}`)

export const getTopPageRankProducts = (limit = 10) =>
  request<TopPageRankProduct[]>(`/dashboard/products/top-pagerank${qs({ limit })}`)

export const getBoughtTogether = (productId?: string, limit = 10) =>
  request<BoughtTogetherPair[]>(
    `/dashboard/products/bought-together${qs({ product_id: productId, limit })}`,
  )

export const getRfmSummary = () => request<RfmSegmentSummary[]>('/dashboard/customers/rfm-summary')

export const getCustomers = (segment?: string, limit = 50, offset = 0) =>
  request<CustomerSummary[]>(`/dashboard/customers${qs({ segment, limit, offset })}`)

export const getCustomer = (customerId: string) =>
  request<CustomerDetail>(`/dashboard/customers/${encodeURIComponent(customerId)}`)

export const getSyncStatus = () => request<SyncStatus>('/dashboard/sync-status')

// Catálogo (para os seletores de ação)
export const getCompanies = () => request<Company[]>('/companies')

export const getIntegrations = () => request<Integration[]>('/integrations')

// Ações (jobs em background / triggers)
export const syncIntegration = (integrationId: string) =>
  request<TriggerResponse>(`/integrations/${integrationId}/sync`, { method: 'POST' })

export const triggerGraphSync = () =>
  request<TriggerResponse>('/orders/graph-sync', { method: 'POST' })

export const triggerAlgorithmsRun = () =>
  request<TriggerResponse>('/graph-algorithms/run', { method: 'POST' })

export const triggerEmbeddingsRun = () =>
  request<TriggerResponse>('/embeddings/run', { method: 'POST' })

// Recomendações
export const recommendByProduct = (productId: string, limit = 10) =>
  request<RecommendationResult[]>('/graph-algorithms/recommendations/product', {
    method: 'POST',
    body: JSON.stringify({ product_id: productId, limit }),
  })

export const recommendByCustomer = (customerId: string, limit = 10) =>
  request<RecommendationResult[]>('/graph-algorithms/recommendations/customer', {
    method: 'POST',
    body: JSON.stringify({ customer_id: customerId, limit }),
  })

// Oráculo
export const askOracle = (question: string, topK = 5) =>
  request<AskResponse>('/rag/ask', {
    method: 'POST',
    body: JSON.stringify({ question, top_k: topK }),
  })

/**
 * Variante em streaming de `askOracle` (`POST /rag/ask/stream`, SSE). Não dá
 * pra usar a `EventSource` nativa do browser aqui — ela só faz GET, e este
 * endpoint precisa de um corpo POST (`question`/`top_k`) — então o parsing
 * do formato `data: {...}\n\n` é feito manualmente sobre o `ReadableStream`
 * do `fetch`. `onEvent` é chamado uma vez por evento, na ordem em que chegam
 * (`route` primeiro, depois `meta`, depois vários `token`, terminando em
 * `done` ou `error`).
 */
export async function streamOracleAsk(
  question: string,
  topK: number,
  onEvent: (event: OracleStreamEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  const response = await fetch(`${BASE_URL}/rag/ask/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, top_k: topK }),
    signal,
  })

  if (!response.ok || !response.body) {
    throw new ApiError(response.status, `Erro ${response.status} ao perguntar`)
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })

    let boundary = buffer.indexOf('\n\n')
    while (boundary !== -1) {
      const rawEvent = buffer.slice(0, boundary)
      buffer = buffer.slice(boundary + 2)

      const dataLine = rawEvent.split('\n').find((line) => line.startsWith('data: '))
      if (dataLine) {
        try {
          onEvent(JSON.parse(dataLine.slice('data: '.length)) as OracleStreamEvent)
        } catch {
          // linha malformada (não deveria acontecer vindo do backend) — ignora
        }
      }
      boundary = buffer.indexOf('\n\n')
    }
  }
}
