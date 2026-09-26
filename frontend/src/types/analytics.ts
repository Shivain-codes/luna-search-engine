export interface TopQuery {
  query: string
  count: number
}

export interface ZeroResultQuery {
  query: string
  count: number
}

export interface LatencyStats {
  p50: number | null
  p95: number | null
  p99: number | null
  samples: number
}

export interface QueryAnalytics {
  range: { start: string | null; end: string | null }
  total_queries: number
  top_queries: TopQuery[]
  zero_result_queries: ZeroResultQuery[]
  click_through_rate: number | null
  latency: LatencyStats
}
