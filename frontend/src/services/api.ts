import type { ClickPayload, SearchParams, SearchResponse, SuggestResponse } from '@/types/search'
import type {
  APIKey,
  APIKeyCreated,
  AuditEvent,
  AuthTokens,
  CrawlJob,
  CrawlJobCreate,
  IndexStats,
  QueueStats,
  Setting,
} from '@/types/admin'
import type { QueryAnalytics } from '@/types/analytics'

const API_URL = 'http://localhost:8000'
const TOKEN_KEY = 'luna_access_token'

export interface ApiError {
  code: string
  message: string
  status: number
}

class ApiClient {
  private token: string | null = null
  private onUnauthorized?: () => void

  setUnauthorizedHandler(handler: () => void) {
    this.onUnauthorized = handler
  }

  setToken(token: string) {
    this.token = token
    localStorage.setItem(TOKEN_KEY, token)
  }

  clearToken() {
    this.token = null
    localStorage.removeItem(TOKEN_KEY)
  }

  getToken(): string | null {
    if (!this.token) this.token = localStorage.getItem(TOKEN_KEY)
    return this.token
  }

  isAuthenticated(): boolean {
    return !!this.getToken()
  }

  private async request<T>(
    method: string,
    path: string,
    options: { body?: unknown; params?: Record<string, unknown>; auth?: boolean } = {}
  ): Promise<T> {
    const url = new URL(`${API_URL}${path}`)
    if (options.params) {
      for (const [key, value] of Object.entries(options.params)) {
        if (value !== undefined && value !== null && value !== '') {
          url.searchParams.set(key, String(value))
        }
      }
    }

    const headers: Record<string, string> = { 'Content-Type': 'application/json' }
    if (options.auth !== false) {
      const token = this.getToken()
      if (token) headers.Authorization = `Bearer ${token}`
    }

    const resp = await fetch(url.toString(), {
      method,
      headers,
      body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
    })

    if (resp.status === 401 && options.auth !== false) {
      this.clearToken()
      this.onUnauthorized?.()
    }

    if (!resp.ok) {
      let code = 'ERROR'
      let message = resp.statusText
      try {
        const data = await resp.json()
        if (data?.error) {
          code = data.error.code
          message = data.error.message
        }
      } catch {
        /* ignore */
      }

      // We throw the raw ApiError; the UI/Hooks will use mapApiError to display it.
      throw { code, message, status: resp.status } as ApiError
    }

    if (resp.status === 204) return undefined as T
    return (await resp.json()) as T
  }

  // ---- Public search ----
  search(params: SearchParams): Promise<SearchResponse> {
    return this.request<SearchResponse>('GET', '/api/v1/search', {
      params: { ...params },
      auth: false,
    })
  }

  suggest(q: string, limit = 10): Promise<SuggestResponse> {
    return this.request<SuggestResponse>('GET', '/api/v1/suggest', {
      params: { q, limit },
      auth: false,
    })
  }

  trackClick(payload: ClickPayload): Promise<void> {
    return this.request<void>('POST', '/api/v1/clicks', { body: payload, auth: false })
  }

  runCrawl(jobId: string, maxPages = 25): Promise<{ job_id: string; processed: number; recovered: number }> {
    return this.request<{ job_id: string; processed: number; recovered: number }>(
      'POST',
      '/crawler-api/api/v1/crawl/run',
      { body: { job_id: jobId, max_pages: maxPages } },
    )
  }

  // ---- Auth ----
  async login(email: string, password: string): Promise<AuthTokens> {
    const tokens = await this.request<AuthTokens>('POST', '/api/v1/auth/login', {
      body: { email, password },
      auth: false,
    })
    this.setToken(tokens.access_token)
    return tokens
  }

  // ---- Admin: crawl ----
  listCrawlJobs(status?: string): Promise<CrawlJob[]> {
    return this.request<CrawlJob[]>('GET', '/api/v1/admin/crawl/jobs', { params: { status } })
  }

  createCrawlJob(data: CrawlJobCreate): Promise<CrawlJob> {
    return this.request<CrawlJob>('POST', '/api/v1/admin/crawl/jobs', { body: data })
  }

  updateCrawlJob(id: string, action: string): Promise<CrawlJob> {
    return this.request<CrawlJob>('PATCH', `/api/v1/admin/crawl/jobs/${id}`, { body: { action } })
  }

  queueStats(): Promise<QueueStats> {
    return this.request<QueueStats>('GET', '/api/v1/admin/crawl/queue/stats')
  }

  // ---- Admin: index & analytics ----
  indexStats(): Promise<IndexStats> {
    return this.request<IndexStats>('GET', '/api/v1/admin/index/stats')
  }

  queryAnalytics(params?: { start_date?: string; end_date?: string }): Promise<QueryAnalytics> {
    return this.request<QueryAnalytics>('GET', '/api/v1/admin/analytics/queries', {
      params: params as Record<string, unknown>,
    })
  }

  // ---- Admin: settings ----
  listSettings(): Promise<Setting[]> {
    return this.request<Setting[]>('GET', '/api/v1/admin/settings')
  }

  updateSetting(key: string, value: string): Promise<Setting> {
    return this.request<Setting>('PUT', `/api/v1/admin/settings/${key}`, { body: { value } })
  }

  // ---- Admin: API keys ----
  listApiKeys(): Promise<APIKey[]> {
    return this.request<APIKey[]>('GET', '/api/v1/admin/api-keys')
  }

  createApiKey(name: string, rateLimit = 1000): Promise<APIKeyCreated> {
    return this.request<APIKeyCreated>('POST', '/api/v1/admin/api-keys', {
      body: { name, rate_limit: rateLimit },
    })
  }

  revokeApiKey(id: string): Promise<void> {
    return this.request<void>('DELETE', `/api/v1/admin/api-keys/${id}`)
  }

  listAudit(): Promise<AuditEvent[]> {
    return this.request<AuditEvent[]>('GET', '/api/v1/admin/audit')
  }
}

export const api = new ApiClient()
