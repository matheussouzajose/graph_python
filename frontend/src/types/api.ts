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
  is_active: boolean
  // 'never_synced' | 'running' | 'idle'
  status: string
  last_synced_at: string | null
  synced_until: string | null
  resource_statuses: IntegrationResourceSyncStatus[]
}

export interface IntegrationResourceSyncStatus {
  resource: string
  status: string
  last_synced_at: string | null
  synced_until: string | null
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

export interface IntegrationCreateInput {
  company_id: string
  provider: 'vesti'
  name: string
  base_url: string
  configs: Record<string, unknown>
  params: Record<string, unknown>
  is_active?: boolean
}

export interface IntegrationUpdateInput {
  name?: string
  base_url?: string
  configs?: Record<string, unknown>
  params?: Record<string, unknown>
  is_active?: boolean
}

export interface Product {
  id: string
  integration_id: string
  external_product_id: string
  external_company_id: string
  integration_product_id: string | null
  code: string | null
  name: string | null
  description: string | null
  full_description: string | null
  composition: string | null
  active: boolean
  price: number | null
  promotion: boolean
  price_promotional: number | null
  slug: string | null
  url: string | null
  weight: number | null
  height: number | null
  width: number | null
  length: number | null
  external_created_at: string | null
  external_updated_at: string | null
  release_at: string | null
  order_date: string | null
  brand: Record<string, unknown>
  categories: Record<string, unknown>[]
  negotiations: Record<string, unknown>[]
  sizes: Record<string, unknown>[]
  colors: Record<string, unknown>[]
  stocks: Record<string, unknown>[]
  media: Record<string, unknown>[]
  image_url: string | null
  image_fallback_url: string | null
  created_at: string
  updated_at: string
}

export interface ProductListResponse {
  items: Product[]
  total: number
  limit: number
  offset: number
}

// Um dos 12 arquétipos junguianos de marca (ver docs/arquetipos-de-marca.md
// e app/features/brand_archetype/schemas.py::BrandArchetype).
export type BrandArchetype =
  | 'innocent'
  | 'explorer'
  | 'sage'
  | 'hero'
  | 'outlaw'
  | 'magician'
  | 'everyman'
  | 'jester'
  | 'lover'
  | 'ruler'
  | 'creator'
  | 'caregiver'

export interface BrandVoice {
  tone: string[]
  sentence_style: string | null
  vocabulary_prefer: string[]
  vocabulary_avoid: string[]
}

export interface BrandAudience {
  who: string | null
  speaks_to_them_as: string | null
}

export interface BrandGuardrails {
  do: string[]
  dont: string[]
}

export interface BrandArchetypeProfile {
  id: string
  company_id: string
  primary_archetype: BrandArchetype
  secondary_archetype: BrandArchetype | null
  archetype_scores: Record<string, number>
  core_desire: string | null
  fear: string | null
  strategy: string | null
  voice: BrandVoice
  audience: BrandAudience
  messaging_pillars: string[]
  guardrails: BrandGuardrails
  reference_examples: string[]
  created_at: string
  updated_at: string
}

export interface BrandArchetypeProfileCreateInput {
  company_id: string
  primary_archetype: BrandArchetype
  secondary_archetype?: BrandArchetype | null
  core_desire?: string | null
  fear?: string | null
  strategy?: string | null
  voice?: Partial<BrandVoice>
  audience?: Partial<BrandAudience>
  messaging_pillars?: string[]
  guardrails?: Partial<BrandGuardrails>
  reference_examples?: string[]
}

export type BrandArchetypeProfileUpdateInput = Omit<
  BrandArchetypeProfileCreateInput,
  'company_id'
>

export type AgentResponseFormat = 'text' | 'json'

// "chat" = pergunta/resposta via LLM (comportamento original). "image_to_video"
// submete um job de geração de vídeo (OpenAI Sora) a partir de uma imagem —
// ver app/features/agents/service.py::run. Não editável depois de criado.
export type AgentKind = 'chat' | 'image_to_video'

// Resoluções aceitas pela Sora (largura x altura) — ver
// app/features/agents/schemas.py::VideoSize.
export type VideoSize = '720x1280' | '1280x720' | '1024x1792' | '1792x1024'
export type VideoSeconds = '4' | '8' | '12'

// "none" = resultado é só pra exibir. Outros valores identificam uma ação
// registrada no backend (app/features/agents/actions.py) que sabe o que
// fazer com o resultado estruturado de uma execução — ver
// AGENT_OUTPUT_ACTIONS em lib/agent-actions.ts para os rótulos.
export type AgentOutputAction = 'none' | 'apply_brand_archetype'

export interface Agent {
  id: string
  company_id: string
  name: string
  description: string | null
  kind: AgentKind
  usage_instructions: string | null
  system_prompt: string
  model: string | null
  temperature: number
  uses_brand_archetype: boolean
  response_format: AgentResponseFormat
  output_action: AgentOutputAction
  video_size: VideoSize | null
  video_seconds: VideoSeconds | null
  is_active: boolean
  is_global: boolean
  created_at: string
  updated_at: string
}

export interface AgentCreateInput {
  company_id: string
  name: string
  description?: string | null
  kind?: AgentKind
  usage_instructions?: string | null
  system_prompt: string
  model?: string | null
  temperature?: number
  uses_brand_archetype?: boolean
  response_format?: AgentResponseFormat
  output_action?: AgentOutputAction
  video_size?: VideoSize | null
  video_seconds?: VideoSeconds | null
  is_active?: boolean
  is_global?: boolean
}

export type AgentUpdateInput = Partial<Omit<AgentCreateInput, 'company_id' | 'kind'>>

export interface AgentRunOutput {
  text: string
  data: Record<string, unknown> | null
  // Set once a kind="image_to_video" run completes — a relative API path
  // (`/agent-runs/{id}/video`) that must be fetched with an Authorization
  // header (never used directly as a plain <video src>), see
  // `fetchAgentRunVideo` in lib/api.ts.
  video_url: string | null
}

export interface AgentRunInput {
  message: string
  variables: Record<string, unknown>
  image_urls?: string[]
}

export interface AgentRun {
  id: string
  agent_id: string
  company_id: string
  input: AgentRunInput
  output: AgentRunOutput | null
  status: 'pending' | 'running' | 'completed' | 'failed' | string
  error: string | null
  created_at: string
  updated_at: string
}

export interface AgentRunRequestInput {
  message: string
  variables?: Record<string, unknown>
  image_urls?: string[]
}

// Eventos do SSE de POST /agents/{id}/run/stream (ver app/features/agents/router.py).
export interface AgentStreamEvent {
  type: 'token' | 'error' | 'done'
  text?: string
  message?: string
  run?: AgentRun
}

export interface AgentRunApplyResponse {
  action: string
  result: Record<string, unknown>
}

export interface Order {
  id: string
  integration_id: string
  external_order_id: string
  external_company_id: string
  code: number | null
  origin: string | null
  status: string | null
  observations: string | null
  is_unified: boolean
  survey_note: number | null
  survey_comment: string | null
  external_created_at: string | null
  external_updated_at: string | null
  expires_at: string | null
  customer: Record<string, unknown>
  products: Record<string, unknown>[]
  address: Record<string, unknown>
  freight: Record<string, unknown>
  seller: Record<string, unknown>
  payment: Record<string, unknown>
  summary: Record<string, unknown>
  created_at: string
  updated_at: string
}

export interface OrderListResponse {
  items: Order[]
  total: number
  limit: number
  offset: number
}

export interface OrderFilterOption {
  value: string
  label: string
  count: number
}

export interface OrderFilterFacet {
  key: string
  label: string
  options: OrderFilterOption[]
}

export interface OrderFiltersResponse {
  facets: OrderFilterFacet[]
}

export type OrderFilterParams = Record<string, string[]>

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

export interface ChatSession {
  id: string
  title: string
  created_at: string
  updated_at: string
}

export interface ChatMessage {
  id: string
  session_id: string
  role: 'user' | 'assistant'
  content: string
  route: 'LOCAL' | 'GLOBAL' | null
  generated_query: string | null
  sources: AskSource[] | null
  created_at: string
}

export interface ChatHistory {
  session: ChatSession
  messages: ChatMessage[]
}

// Eventos do SSE de POST /rag/ask/stream (ver app/features/rag/router.py).
// `type` decide quais dos outros campos vêm preenchidos.
export interface OracleStreamEvent {
  type: 'route' | 'meta' | 'token' | 'error' | 'done' | 'question' | 'replace'
  route?: 'LOCAL' | 'GLOBAL'
  sources?: AskSource[]
  generated_query?: string
  text?: string
  message?: string
  standalone_question?: string
}
