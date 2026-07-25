import type {
  AskResponse,
  BoughtTogetherPair,
  ChatHistory,
  ChatSession,
  Company,
  CustomerDetail,
  CustomerSummary,
  Integration,
  IntegrationUpdateInput,
  LoginResponse,
  OracleStreamEvent,
  OrderFilterParams,
  OrderFiltersResponse,
  OrderListResponse,
  Overview,
  RecommendationResult,
  RfmSegmentSummary,
  SyncStatus,
  TopPageRankProduct,
  TopRevenueProduct,
  TopSellingProduct,
  TriggerResponse,
} from '@/types/api'
import { clearStoredAccessToken, getStoredAccessToken } from '@/lib/auth-token'

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api/v1'

export class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const token = getStoredAccessToken()
  const response = await fetch(`${BASE_URL}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...init?.headers,
    },
  })

  if (!response.ok) {
    if (response.status === 401) {
      clearStoredAccessToken()
    }
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

export const login = (email: string, password: string) =>
  request<LoginResponse>('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  })

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

function filterQs(
  filters: OrderFilterParams,
  params: Record<string, string | number | boolean | null | undefined> = {},
): string {
  const search = new URLSearchParams()
  for (const [key, values] of Object.entries(filters)) {
    for (const value of values) {
      if (value) search.append(key, value)
    }
  }
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

export const updateIntegration = (integrationId: string, data: IntegrationUpdateInput) =>
  request<Integration>(`/integrations/${integrationId}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  })

export const deleteIntegration = (integrationId: string) =>
  request<void>(`/integrations/${integrationId}`, { method: 'DELETE' })

// Pedidos
export const getOrders = (filters: OrderFilterParams = {}, limit = 50, offset = 0) =>
  request<OrderListResponse>(`/orders${filterQs(filters, { limit, offset })}`)

export const getOrderFilters = (filters: OrderFilterParams = {}, optionLimit = 40) =>
  request<OrderFiltersResponse>(`/orders/filters${filterQs(filters, { option_limit: optionLimit })}`)

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

export const createChatSession = (title?: string) =>
  request<ChatSession>('/rag/chat/sessions', {
    method: 'POST',
    body: JSON.stringify({ title }),
  })

export const getChatSessions = (limit = 30) =>
  request<ChatSession[]>(`/rag/chat/sessions${qs({ limit })}`)

export const getChatHistory = (sessionId: string) =>
  request<ChatHistory>(`/rag/chat/sessions/${encodeURIComponent(sessionId)}`)

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
    headers: {
      'Content-Type': 'application/json',
      ...(getStoredAccessToken()
        ? { Authorization: `Bearer ${getStoredAccessToken()}` }
        : {}),
    },
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

export async function streamChatMessage(
  sessionId: string,
  message: string,
  topK: number,
  onEvent: (event: OracleStreamEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  const response = await fetch(`${BASE_URL}/rag/chat/sessions/${encodeURIComponent(sessionId)}/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(getStoredAccessToken()
        ? { Authorization: `Bearer ${getStoredAccessToken()}` }
        : {}),
    },
    body: JSON.stringify({ message, top_k: topK }),
    signal,
  })

  if (!response.ok || !response.body) {
    throw new ApiError(response.status, `Erro ${response.status} ao conversar`)
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
          // ignora evento malformado
        }
      }
      boundary = buffer.indexOf('\n\n')
    }
  }
}
