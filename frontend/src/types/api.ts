// Tipos espelhando os schemas Pydantic do backend (app/features/*/schemas.py).
// Mantidos manualmente — sem gerador de client, o projeto ainda não expõe
// um contrato tipado (ex: openapi-typescript) para isso.

export interface OrderStatusCount {
  status: string
  count: number
}

export interface Overview {
  total_revenue: number
  total_orders: number
  average_ticket: number
  unique_customers: number
  products_sold: number
  orders_by_status: OrderStatusCount[]
  last_order_sync_at: string | null
  last_algorithms_run_at: string | null
}

export interface TopSellingProduct {
  product_id: string
  product_name: string | null
  product_code: string | null
  quantity_sold: number
}

export interface TopRevenueProduct {
  product_id: string
  product_name: string | null
  product_code: string | null
  revenue: number
}

export interface TopPageRankProduct {
  product_id: string
  product_name: string | null
  product_code: string | null
  pagerank: number
}

export interface BoughtTogetherPair {
  product_id: string
  product_name: string | null
  product_code: string | null
  related_product_id: string
  related_product_name: string | null
  related_product_code: string | null
  support_count: number
  confidence: number
  lift: number
}

export interface RfmSegmentSummary {
  segment: string
  customer_count: number
  avg_recency_days: number | null
  avg_frequency: number | null
  avg_monetary: number | null
}

export interface CustomerSummary {
  customer_id: string
  name: string | null
  email: string | null
  document: string | null
  rfm_segment: string | null
  rfm_score: number | null
  rfm_recency_days: number | null
  rfm_frequency: number | null
  rfm_monetary: number | null
  last_order_at: string | null
  city_name: string | null
  state_initials: string | null
}

export interface CustomerPurchasedProduct {
  product_id: string
  name: string | null
  code: string | null
}

export interface CustomerDetail extends CustomerSummary {
  products_purchased: CustomerPurchasedProduct[]
}

export interface IntegrationSyncStatus {
  integration_id: string
  integration_name: string
  provider: string
  status: string
  last_synced_at: string | null
}

export interface AlgorithmRunStatus {
  name: string
  computed_at: string | null
}

export interface SyncStatus {
  integrations: IntegrationSyncStatus[]
  algorithm_runs: AlgorithmRunStatus[]
}

export interface Company {
  id: string
  name: string
  domain_id: number
  external_company_id: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface User {
  id: string
  company_id: string
  email: string
  name: string
  role: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface AuthUser {
  id: string
  company_id: string
  email: string
  name: string
  role: string
}

export interface LoginResponse {
  access_token: string
  token_type: 'bearer' | string
  user: User
}

export interface Integration {
  id: string
  company_id: string
  provider: string
  name: string
  base_url: string
  configs: Record<string, unknown>
  params: Record<string, unknown>
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface IntegrationUpdateInput {
  name?: string
  base_url?: string
  configs?: Record<string, unknown>
  params?: Record<string, unknown>
  is_active?: boolean
}

export interface TriggerResponse {
  status: 'accepted' | 'already_running' | string
  integration_id?: string | null
}

export type RecommendationReason =
  | 'similaridade'
  | 'comprado_junto'
  | 'similar_ao_historico'
  | 'comprado_junto_ao_historico'
  | string

export interface RecommendationResult {
  product_id: string
  product_name: string | null
  product_code: string | null
  score: number
  reasons: RecommendationReason[]
  similarity_score: number
  support_count: number
  confidence: number
  lift: number
  pagerank: number | null
  customer_segment: string | null
  customer_rfm_score: number | null
}

export interface AskSource {
  order_code: string | null
  product_code: string | null
  customer_name: string | null
  score: number | null
}

export interface AskResponse {
  route: 'LOCAL' | 'GLOBAL'
  answer: string | null
  generated_query: string | null
  sources: AskSource[] | null
}

// Eventos do SSE de POST /rag/ask/stream (ver app/features/rag/router.py).
// `type` decide quais dos outros campos vêm preenchidos.
export interface OracleStreamEvent {
  type: 'route' | 'meta' | 'token' | 'error' | 'done'
  route?: 'LOCAL' | 'GLOBAL'
  sources?: AskSource[]
  generated_query?: string
  text?: string
  message?: string
}
