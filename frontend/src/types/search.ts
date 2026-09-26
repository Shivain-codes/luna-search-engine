export interface KnowledgeContext {
  name: string
  category?: string
  description?: string
  image?: string
  facts?: Record<string, string | number | boolean>
}

export interface SearchResult {
  id: string
  url: string
  title: string | null
  snippet: string
  score: number
  pagerank: number
  crawled_at: string
  images?: string[]
}

export interface SearchResponse {
  query: string
  normalized_query: string
  corrected_query: string | null
  results: SearchResult[]
  total_results: number
  page: number
  per_page: number
  total_pages: number
  search_time_ms: number
  cache_hit: boolean
  query_context: KnowledgeContext | null
  answer?: string | null
}

export interface Suggestion {
  text: string
  type: string
  description?: string
}

export interface SuggestResponse {
  query: string
  suggestions: Suggestion[]
}

export interface SearchParams {
  q: string
  page?: number
  per_page?: number
  site?: string
  language?: string
  safe_search?: boolean
  date_range?: string
}

export interface ClickPayload {
  query_context: string
  document_id: string
  position: number
  dwell_time_ms?: number
}
