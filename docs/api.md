# API Reference

Base URL (local): `http://localhost:8000`. All endpoints are versioned under
`/api/v1`. Timestamps are UTC ISO-8601. Every response carries an
`X-Request-ID` header.

## Error envelope

All errors share one shape:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Human readable message",
    "details": {},
    "request_id": "uuid"
  }
}
```

Status codes: `422` validation, `401` unauthenticated, `403` forbidden,
`404` not found, `429` rate limited, `502` dependency unavailable,
`504` dependency timeout.

## Health

- `GET /health/live` — process liveness.
- `GET /health/ready` — dependency readiness (503 if degraded).
- `GET /health` — combined status with dependency latencies.

## Public search

### `GET /api/v1/search`

Query params: `q` (required, 1–500 chars), `page` (≥1), `per_page`
(1–50), `site`, `language`, `safe_search`, `date_range`.

`q` supports operators: `+required`, `-excluded`, `"exact phrase"`, `site:`,
`intitle:`, `inurl:`.

```json
{
  "query": "python programming",
  "normalized_query": "python programming",
  "corrected_query": null,
  "results": [
    {
      "id": "uuid",
      "url": "https://docs.nexus.dev/python",
      "title": "Python Programming Guide",
      "snippet": "...matching text...",
      "score": 8.371,
      "pagerank": 0.0421,
      "crawled_at": "2025-01-01T00:00:00Z"
    }
  ],
  "total_results": 6,
  "page": 1,
  "per_page": 10,
  "total_pages": 1,
  "search_time_ms": 12.4,
  "cache_hit": false,
  "query_context": "opaque-id"
}
```

### `GET /api/v1/suggest`

Query params: `q` (required), `limit` (1–20). Returns typed suggestions:

```json
{ "query": "py", "suggestions": [ { "text": "python programming", "type": "query" } ] }
```

### `POST /api/v1/clicks`

Body: `{ "query_context", "document_id", "position", "dwell_time_ms"? }`.
Records a result click for analytics. Returns `202`. Non-blocking.

## Authentication

### `POST /api/v1/auth/login`

Body `{ "email", "password" }` → `{ access_token, refresh_token, token_type, expires_in }`.

### `POST /api/v1/auth/refresh?refresh_token=...`

Returns a new token pair.

Send the access token as `Authorization: Bearer <token>` on admin routes.

## Admin (JWT required; role-gated)

| Method & path | Permission | Description |
|---|---|---|
| `GET /api/v1/admin/crawl/jobs` | crawl:read | List crawl jobs |
| `POST /api/v1/admin/crawl/jobs` | crawl:write | Create a crawl job |
| `GET /api/v1/admin/crawl/jobs/{id}` | crawl:read | Job detail |
| `PATCH /api/v1/admin/crawl/jobs/{id}` | crawl:write | `{ "action": "pause\|resume\|cancel" }` |
| `GET /api/v1/admin/crawl/queue/stats` | crawl:read | Frontier statistics |
| `GET /api/v1/admin/index/stats` | analytics:read | Documents / postings / terms |
| `GET /api/v1/admin/analytics/queries` | analytics:read | Volume, top/zero-result queries, CTR, latency percentiles |
| `GET /api/v1/admin/settings` | settings:read | List settings |
| `PUT /api/v1/admin/settings/{key}` | settings:write | Update an allowlisted setting |
| `GET /api/v1/admin/api-keys` | apikey:manage | List keys (no plaintext) |
| `POST /api/v1/admin/api-keys` | apikey:manage | Create key (plaintext returned once) |
| `DELETE /api/v1/admin/api-keys/{id}` | apikey:manage | Revoke a key |
| `GET /api/v1/admin/audit` | audit:read | Recent audit events |

Roles: `viewer` (read), `operator` (+ crawl/settings write), `admin` (all).

## Internal service endpoints

- Ranker `POST /api/v1/rank/score`, `POST /api/v1/rank/pagerank`, `GET /api/v1/rank/stats`
- Indexer `POST /api/v1/index`
- Crawler `POST /api/v1/crawl/run`, `GET /api/v1/crawl/queue/stats`

These are not exposed publicly through the gateway.
