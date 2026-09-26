export type CrawlStatus =
  | 'pending'
  | 'running'
  | 'paused'
  | 'completed'
  | 'failed'
  | 'cancelled'

export interface CrawlJob {
  id: string
  name: string
  seed_urls: string[]
  allowed_domains: string[]
  status: CrawlStatus
  priority: number
  max_depth: number
  max_pages: number
  total_pages: number
  pages_crawled: number
  pages_failed: number
  created_at: string | null
  started_at: string | null
  completed_at: string | null
  error_message: string | null
}

export interface CrawlJobCreate {
  name: string
  seed_urls: string[]
  allowed_domains?: string[]
  blocked_domains?: string[]
  max_depth?: number
  max_pages?: number
  priority?: number
}

export interface QueueStats {
  pending: number
  in_progress: number
  done: number
  failed: number
  total: number
  domains: Record<string, number>
}

export interface IndexStats {
  documents: number
  postings: number
  terms: number
}

export interface Setting {
  key: string
  value: string
  description: string | null
  category: string
}

export interface APIKey {
  id: string
  name: string
  key_prefix: string
  is_active: boolean
  rate_limit: number
  created_at: string | null
  last_used_at: string | null
}

export interface APIKeyCreated extends APIKey {
  key: string
}

export interface AuditEvent {
  id: string
  action: string
  actor_role: string | null
  target_type: string | null
  target_id: string | null
  outcome: string
  created_at: string | null
}

export interface AuthTokens {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
}
