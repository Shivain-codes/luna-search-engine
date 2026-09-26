# Luna Complete Search Engine Design

## Overview

Luna is completed as an incremental stabilization of the existing Dockerized microservice architecture, not as a replacement architecture. The design preserves the service names and ports already declared in `docker-compose.yml` and `IMPLEMENTATION_PLAN.md`:

- API Gateway: `8000`
- Search API: `8001`
- Ranker: `8004`
- Admin API: `8005`
- Frontend: `3000`
- PostgreSQL: `5432`
- Redis: `6379`
- RabbitMQ: `5672` and management UI `15672`

The implementation language remains Python 3.13/FastAPI/SQLAlchemy/Alembic/Pydantic for backend services and React 18/TypeScript/Vite/Tailwind for the frontend. PostgreSQL remains the source of truth for durable state, Redis remains the cache and short-lived coordination layer, and RabbitMQ remains the durable asynchronous pipeline transport.

### Repository constraints

The current repository is partial and is treated as a first-class design constraint:

- The Compose file declares all services, but service images and runtime contracts need a common startup/readiness convention.
- Alembic revisions exist, while mounting the `migrations` directory as PostgreSQL init scripts is not a valid way to execute Python migrations. Alembic must become the authoritative migration runner.
- Gateway, Search API, Crawler, Indexer, and Ranker contain partial implementations with overlapping local models/algorithms. Shared code is consolidated without moving business ownership into the shared package.
- Admin API has a partial authentication, crawl, settings, index, analytics, and API-key surface that must be aligned to the same contracts and RBAC policy.
- `frontend/src/App.tsx` references pages, layout components, and a `Toaster` that are not present; `frontend/src/pages` is empty and `frontend/src/components` only contains an empty/incomplete `ui` boundary. These modules are completed before feature behavior is evaluated.
- `shared/typescript`, `scripts`, and `docs` are empty or incomplete and are added incrementally rather than assumed to exist.
- Existing crawler and ranking YAML files are configurable defaults and starting points, not evidence that production crawl rates or latency goals have been achieved.

The stabilization principle is to make the smallest vertical slice runnable first, then add pipeline behavior, frontend/admin/analytics behavior, operations/documentation, and finally layered validation and optional benchmarks.

### Demo data and operator workflow

The repository gains a deterministic offline loader at `scripts/seed_demo_data.py` or an equivalent documented module entrypoint. It uses bundled/generated fixtures rather than the network and is safe to run repeatedly through upserts and stable fixture IDs. The fixture set contains:

- representative HTML-derived documents across several domains and languages;
- crawl jobs, normalized frontier entries, counters, and terminal statuses;
- extracted documents and positional postings for title/headings/body/metadata/URL;
- term statistics and deterministic PageRank values for a small link graph;
- query logs including normal, corrected, zero-result, filtered, and paginated examples;
- click logs with positions and dwell times;
- autocomplete source terms from query logs, titles, URLs, and indexed terms;
- at least one active admin per documented role, with development-only credentials clearly marked.

The loader reports inserted, skipped, updated, and total records by category. A second invocation produces no duplicate logical records. If an optional external-crawl demo is enabled, it requires explicit seeds/domains and writes source/retrieval metadata; the offline path remains the default portfolio workflow.

The documented happy path is:

1. Copy `.env.example` to a development environment and review warnings.
2. Build/start infrastructure and run the migration gate.
3. Start application services and wait for readiness.
4. Run the offline demo-data command.
5. Open the frontend and execute search and suggestion flows.
6. Log in using the development admin fixture.
7. Inspect crawl/index controls and analytics.
8. Optionally create, pause, resume, or cancel a controlled local crawl job.
9. Run the validation summary.

### Implementation order and non-goals

The implementation follows the task plan’s gates and phases:

1. Repository inventory, package/build stabilization, frontend compilation, shared lifecycle primitives, and the single Alembic migration gate.
2. SQLAlchemy/Alembic reconciliation, versioned HTTP/message contracts, queue envelopes, health/readiness, and gateway/service adapters.
3. Crawler policy and extraction, durable crawl state, post-commit indexing, positional postings/statistics, BM25/PageRank, and the Search API vertical slice.
4. Frontend routes, typed React Query integration, URL state, search/suggestions/click tracking, responsive accessibility, and recoverable errors.
5. Authentication, refresh/token validation, RBAC, administration, API keys, audit events, analytics, and optional authenticated streams.
6. Operational configuration, resilience/security hardening, offline demo/documentation, layered validation, and optional benchmarks.

Exit conditions are the same as the task checkpoints: the repository must build and migrate before contract work; a controlled crawl fixture must become indexed, ranked, searchable, cached where eligible, and represented in analytics before frontend/admin work; a reviewer must be able to follow the documented demo path; and the final validation summary must distinguish functional results, known limitations, and measured versus unmeasured goals.

The architecture remains microservice-oriented because the repository and Compose topology already establish those boundaries. A single-process fallback may be used for unit tests, but it is not a replacement deployment design. PostgreSQL remains authoritative for durable state; Redis outages may disable caching or live snapshots but must not lose crawl/index/job state. RabbitMQ is used for asynchronous document indexing and operational events, while synchronous HTTP is retained for bounded Search API-to-Ranker scoring.

Learning-to-rank, real-time streams, external-web demo crawling, TLS termination, and benchmark execution are optional capabilities behind configuration and are not prerequisites for the core offline demo. The implementation-plan throughput/latency numbers are not claimed until benchmark infrastructure produces a recorded result. No implementation code is produced by this design document.

## Architecture

### Runtime topology

```text
Browser
  |
  v
Nginx/edge policy (deployment profile; optional in local Compose)
  |
  v
API Gateway :8000
  |-- public /api/v1/search, /api/v1/suggest, /api/v1/clicks --> Search API :8001
  |-- auth and /api/v1/admin/* -------------------------------> Admin API :8005
  |
  +--> Redis :6379 (rate limits, cache, short-lived auth/stream state)

Search API :8001
  |-- PostgreSQL :5432 (documents, postings, terms, query/click logs)
  |-- Redis (query cache, suggestions)
  +-- Ranker :8004 (candidate scoring and graph score reads)

Admin API :8005
  |-- PostgreSQL (jobs, users, settings, audit data, analytics)
  |-- Redis (queue/metrics snapshots and rate limits)
  +-- RabbitMQ :5672 (crawl commands and operational events)

Crawler workers
  |-- PostgreSQL (crawl jobs/frontier/documents)
  |-- Redis (politeness/robots/short-lived locks)
  +-- RabbitMQ (crawl result/index tasks)

Indexer workers
  |-- PostgreSQL (postings and term statistics)
  |-- RabbitMQ (index task consumption, dead-letter handling)

Ranker :8004
  |-- PostgreSQL (document/link graph and persisted PageRank)
  +-- Redis (ranking configuration/cache where enabled)
```

The local Compose profile may expose infrastructure ports for development, but application callers use service names on the Compose network. External clients use only the gateway. Direct Search API, Ranker, and Admin API ports are retained for diagnostics and integration tests and are protected from public exposure in deployment profiles.

### Boundary and ownership rules

Each service owns its use cases and persistence queries. The shared Python package contains only cross-cutting primitives and versioned transport models:

- configuration loading and redacted effective-config reporting;
- SQLAlchemy base/database lifecycle helpers and shared persistence model definitions where the table is genuinely cross-service;
- RabbitMQ exchange/queue names and message envelope types;
- Redis client, cache-key helpers, and bounded retry helpers;
- URL normalization, tokenization primitives, request correlation, structured logging, and security primitives;
- Pydantic schemas for public service contracts when a schema is consumed by more than one service.

The shared package does not contain Search API use cases, crawler orchestration, admin authorization decisions, or ranker business policy. A service may wrap shared primitives with its own domain service and repository layer.

### Internal module layout

The target layout for each Python service is:

```text
services/<service>/
  Dockerfile
  pyproject.toml
  src/<service>/
    main.py                 # app/worker entrypoint and lifespan
    config.py               # service-specific settings adapter
    api/                    # HTTP routers and dependency wiring, if applicable
    domain/                 # use cases, state machines, pure policies
    repositories/           # DB/cache/broker adapters
    schemas/                # service-local request/response schemas
    clients/                # downstream HTTP/broker clients
    observability.py        # metrics/log context wiring
  tests/
    unit/
    integration/
```

Partial implementations can be moved or wrapped into these boundaries incrementally. Duplicate `BM25Index`, HTML processors, settings objects, and auth helpers are first reduced to one canonical implementation per responsibility; compatibility wrappers may remain temporarily while tests are migrated.

### Configuration and dependency lifecycle

Configuration is loaded in this order:

1. typed code defaults safe for local development;
2. `config/crawler.yaml` and `config/ranking.yaml` for policy defaults;
3. environment variables for deployment overrides;
4. persisted Admin settings only for explicitly allowlisted runtime-tunable values.

Every application follows a common lifespan sequence:

1. Parse and validate settings.
2. Initialize structured logging and request-ID context.
3. Connect to required dependencies with bounded startup retries.
4. Declare/check broker exchanges and queues.
5. Register health/readiness state.
6. Start the HTTP server or worker loop.
7. On shutdown, stop accepting work, finish or negatively acknowledge in-flight work according to policy, flush safe logs/metrics, close broker/cache/database clients, and exit within a configured grace period.

A typed settings object validates URLs, port/range values, positive timeouts, rate limits, cache TTLs, crawler limits, ranking weights, JWT requirements, CORS origins, and production-mode secret requirements. The `.env.example` covers service URLs, database/Redis/RabbitMQ URLs, JWT issuer/audience/secret, CORS, rate limits, cache, timeouts, logging, migration mode, frontend API URL, and production mode. YAML values remain defaults and are not duplicated inconsistently in code.

## Components and Interfaces

### API Gateway

The gateway is the only public application ingress. It owns request ID/correlation ID generation and propagation, CORS, request size, endpoint rate limits, security headers, timeout policy, JWT/API-key extraction, routing to Search API and Admin API using environment-configured URLs, consistent downstream error mapping to `502`/`504`, and redacted access logging.

It does not implement search, crawl, analytics aggregation, or detailed authorization policy. The Admin API remains the source of truth for RBAC decisions. Gateway and Nginx, where enabled, share documented CORS origins, request/body sizes, connection limits, public search/autocomplete limits, rate limits, security headers, trusted-proxy rules, TLS/deployment settings, metrics access, and health exposure.

### Search API

The Search API owns the synchronous Query Pipeline:

1. Validate query and filters.
2. Normalize Unicode, whitespace, case, and URL/operator syntax.
3. Optionally correct or expand the query using configured capabilities.
4. Parse Boolean, phrase, and field operators.
5. Retrieve candidates from the positional inverted index.
6. Request ranking from Ranker or use a controlled fallback only when configured.
7. Apply safe-search/site/language/date/domain filters and diversification.
8. Build snippets and highlighting metadata.
9. Paginate and return the response.
10. Write query analytics asynchronously or through a durable outbox path.
11. Cache only eligible, non-personalized results in Redis.

The Search API owns query normalization and response shaping. Ranker owns score calculation, not HTTP pagination or presentation. Redis cache failure degrades to uncached operation where safe.

### Crawler Service

Crawler workers own crawl-job execution and the URL frontier. The pipeline is:

1. Claim an eligible frontier entry using priority and `scheduled_at` ordering.
2. Reject invalid, duplicate, blocked, out-of-domain, or robots-disallowed URLs before HTTP.
3. Acquire per-domain and global politeness permits.
4. Fetch with configured identity, timeouts, redirect and body-size limits.
5. Classify transient versus terminal failures and apply bounded exponential backoff.
6. Extract content and links from accepted HTML.
7. Upsert the Document by normalized/canonical URL and content identity.
8. Enqueue newly discovered URLs under the job policy.
9. Publish one idempotent `document.index.requested` message after the durable document commit.
10. Update frontier/job counters and status transitions.

Crawler policy is configured through `config/crawler.yaml` plus environment overrides. Robots decisions, URL filtering, retries, and extraction are pure/testable domain modules around I/O adapters. The Politeness Manager uses a per-domain token bucket (`rate = 1/crawl_delay`), a 24-hour robots cache, maximum two concurrent requests per domain, a global maximum of 50 concurrent requests, and exponential backoff on `429`/`5xx` responses. The URL frontier is a priority queue of `(priority, scheduled_at, url)` with seed priority `100`, internal-link priority `50`, external-link priority `10`, normalized URL SHA256 deduplication, depth tracking, and per-domain page limits. Content extraction removes `script`, `style`, `noscript`, `iframe`, `svg`, `canvas`, `header`, `footer`, `nav`, and `aside`; extracts title, meta description, Open Graph, JSON-LD, heading hierarchy, cleaned text, decoded entities, and normalized outlinks; and records language through the configured detector (fastText where enabled).

### Indexer Service

Indexer workers consume `document.index.requested` messages containing a version, idempotency key, document ID, source URL, content hash, extracted fields, and crawl metadata. The indexer parses or validates content, removes configured non-content elements, tokenizes/normalizes configured fields, applies stopwords/stemming, creates positional postings for title, heading, body, metadata, anchor, structured-data, image-alt, and URL fields where available, replaces the target document’s previous postings in one transaction, recalculates affected term statistics and IDF values, and acknowledges only after commit.

Malformed or exhausted messages go to the durable dead-letter queue with failure details. The idempotency key is based on document ID and content hash/version. Re-delivery updates the same logical records rather than appending duplicates.

### Ranker Service

Ranker provides a bounded HTTP contract for candidate scoring and owns pure ranking implementations:

- field-aware BM25 using configured `k1`, `b`, IDF, field weights, and length normalization;
- PageRank over a materialized document link graph with dangling-node handling and convergence limits;
- freshness, phrase, prefix, and configured diversification features;
- optional learning-to-rank feature extraction behind a disabled-by-default flag.

PageRank computation is a worker or scheduled operation, not part of each query request. The persisted `documents.pagerank` value is read by scoring and updated asynchronously at the configured interval. A rank request remains bounded; if Ranker is unavailable, Search API returns a documented degraded error or configured lexical-only response, never an unbounded request.

The configured BM25 formula is:

```text
score = Σ IDF(q) * (f(q,D) * (k1 + 1)) / (f(q,D) + k1 * (1 - b + b * |D|/avgdl))
k1=1.5, b=0.75
IDF = log((N - df + 0.5) / (df + 0.5) + 1)
```

PageRank uses power iteration, damping factor `0.85`, 30 iterations, tolerance `1e-6`, dangling-node handling, and weekly updates by default. Values remain configurable.

### Admin API and Analytics Pipeline

Admin API owns administrator login and refresh token behavior, user/account status and role checks, crawl commands and queue inspection, index statistics, ranking/crawler setting management, API-key lifecycle, analytics aggregation endpoints, audit events, and the optional authenticated operational event stream.

Analytics read models derive from `query_logs` and `click_logs`. Initial implementation may aggregate synchronously with bounded date ranges; a later rollup worker may materialize daily/hourly aggregates without changing the response contract. Missing samples return explicit empty or unavailable values, never fabricated measurements.

### Authentication, security, and RBAC

Passwords are verified with a modern adaptive password hash. Access and refresh JWTs are signed with a configured algorithm and secret/key pair. Claims include subject, role, token type, issued-at, expiry, issuer, and audience. Refresh tokens have a distinct token type and are rotated or revoked according to configuration. Validation checks signature, issuer/audience, expiry, token type, user existence, and active status.

The development default `JWT_SECRET` is explicitly labeled development-only. Production mode refuses placeholder/weak secrets and requires explicit database, broker, CORS, and credential values. Secrets come from environment/secret injection and are never logged or placed in settings responses.

The initial role set matches the existing `viewer`, `operator`, and `admin` intent:

| Capability | viewer | operator | admin |
|---|---:|---:|---:|
| Read index stats and analytics | yes | yes | yes |
| Inspect crawl jobs/queue | yes | yes | yes |
| Create/pause/resume/cancel crawl jobs | no | yes | yes |
| Update crawler/ranking settings | no | limited allowlist | yes |
| Create/revoke API keys | no | no | yes |
| Manage administrators/roles | no | no | yes |
| Read audit events | no | limited | yes |

The permission matrix is centralized in the shared security primitive, while endpoint-specific required permissions remain in Admin API route dependencies. Missing credentials return `401`; valid credentials without permission return `403`. All access decisions use the authenticated principal, never a client-supplied role.

On API-key creation, generate high-entropy plaintext once, return it only in the creation response, and persist a slow/secure hash plus display prefix, owner, IP allowlist, rate limit, active flag, expiry, and last-use timestamp. Authentication compares a supplied key to the stored hash and updates last-use metadata without logging the key.

Every setting, key, role, and crawl-state change writes an audit event containing actor ID, role, action, target type/ID, timestamp, request/correlation ID, outcome, and safe reason. Failed authorization and validation outcomes are recorded where policy permits, with sensitive request fields redacted.

### HTTP interfaces

All HTTP contracts are versioned under `/api/v1`. Pydantic models are the source of truth for Python validation and are mirrored into TypeScript types under `shared/typescript` or generated from an OpenAPI export. The frontend must not hand-maintain divergent field names.

Success responses use JSON and UTC ISO-8601 timestamps. Every request accepts or receives `X-Request-ID`; the gateway creates one when absent and propagates it downstream. The common error shape and status mapping are defined in **Error Handling** below.

The public search interface is:

```text
GET /api/v1/search
q: string, required, bounded length
page: positive integer, default 1
per_page: positive integer, default configured value, max configured value
site: optional host/domain
language: optional language code
safe_search: optional boolean
date_range: optional named range or validated range
```

A response contains:

```json
{
  "query": "original input",
  "normalized_query": "normalized input",
  "corrected_query": "optional correction",
  "results": [
    {
      "id": "document-uuid",
      "url": "https://example.test/page",
      "title": "Title",
      "snippet": "...matching text...",
      "highlights": [{"field": "body", "start": 12, "end": 20}],
      "score": 1.23,
      "pagerank": 0.04,
      "crawled_at": "2025-01-01T00:00:00Z"
    }
  ],
  "total_results": 1,
  "page": 1,
  "per_page": 10,
  "total_pages": 1,
  "search_time_ms": 12.4,
  "cache_hit": false,
  "query_context": "opaque-query-context"
}
```

`GET /api/v1/suggest?q=<partial>&limit=<n>` returns bounded, deterministically ordered suggestions with a type for every item:

```json
{
  "query": "pyth",
  "suggestions": [
    {"text": "python", "type": "query"},
    {"text": "python tutorial", "type": "query"}
  ]
}
```

Suggestions may come from query logs, document titles/URLs, and indexed terms, but the response shape and ordering contract remain stable. `POST /api/v1/clicks` accepts an opaque query context, document ID, result position, and optional dwell time. It validates that the context/document relationship is plausible, writes a click log, and returns `202` or a small accepted response without blocking navigation.

The gateway exposes Admin API routes under `/api/v1/auth/*` and `/api/v1/admin/*`; the Admin API owns the same schemas when called directly in tests:

- `POST /api/v1/auth/login`: `{email,password}` -> `{access_token, refresh_token, token_type, expires_in}`.
- `POST /api/v1/auth/refresh`: refresh token -> replacement access/refresh token pair.
- `GET /api/v1/admin/crawl/jobs?status=&limit=&offset=` -> paginated/listed `CrawlJob` records.
- `POST /api/v1/admin/crawl/jobs` accepts name, seed URLs, domain policy, depth/page limits, politeness settings, user agent, and priority.
- `GET /api/v1/admin/crawl/jobs/{id}` -> job detail/counters/status.
- `PATCH /api/v1/admin/crawl/jobs/{id}` accepts legal control operations (`pause`, `resume`, `cancel`) and safe mutable configuration.
- `GET /api/v1/admin/crawl/queue/stats` -> queue depth, pending/in-flight/failed counts, and domain summaries.
- `GET /api/v1/admin/index/stats` returns document, indexed-document, term, posting, and last-update counts.
- `GET /api/v1/admin/analytics/queries?start_date=&end_date=&limit=` returns the requested range, volume, top queries, zero-result queries, CTR when data exists, and latency statistics with explicit unavailable/null values.
- `GET/POST/PUT /api/v1/admin/settings` validates typed setting keys and records the actor.
- `GET/POST/DELETE /api/v1/admin/api-keys` never returns stored plaintext after creation.

### RabbitMQ interfaces

Use durable topic exchanges and versioned envelopes:

```json
{
  "event_id": "uuid",
  "event_type": "document.index.requested",
  "schema_version": 1,
  "occurred_at": "2025-01-01T00:00:00Z",
  "correlation_id": "uuid",
  "idempotency_key": "document-uuid:content-hash",
  "payload": {
    "document_id": "uuid",
    "url": "https://example.test",
    "content_hash": "sha256",
    "fields": {"title": "...", "body": "...", "headings": [], "outlinks": []}
  }
}
```

Canonical queues are `crawl.commands`, `crawl.results`, `document.index.requested`, `document.index.dead-letter`, and `operational.events`. Messages are durable, acknowledged after commit, and retried with a bounded delivery count. Queue names and routing keys live in shared messaging constants so producers and consumers cannot drift. Publisher confirms, reconnect behavior, and dead-letter routing are part of the shared broker adapter.

### Frontend structure and state flow

The existing React shell, QueryClient, BrowserRouter, Zustand stores, API client, theme styles, and hooks remain. Missing modules are completed into:

```text
frontend/src/
  App.tsx
  main.tsx
  components/
    ui/                  # Button, Input, Card, Modal, Badge, Spinner, Toaster, etc.
    layout/              # Navbar, Footer, ProtectedRoute, PageShell
    search/              # SearchHero, SearchBox, SuggestionList, ResultCard,
                         # SearchResults, Pagination, NoResults
    admin/               # AdminSidebar, KPI cards, CrawlJobTable, queue chart
    analytics/           # volume, top-query, zero-result, latency views
  pages/
    SearchPage.tsx
    ResultsPage.tsx
    LoginPage.tsx
    AdminDashboard.tsx
    AnalyticsDashboard.tsx
    SettingsPage.tsx
    NotFoundPage.tsx
  hooks/
    useSearch.ts
    useAutocomplete.ts
    useClickTracking.ts
    useAuth.ts
    useAdmin.ts
    useAnalytics.ts
    useDebounce.ts
    useTheme.ts
  services/
    api.ts
    contracts.ts          # generated/shared response types
  store/
    searchStore.ts
    themeStore.ts
    adminStore.ts
    authStore.ts
  types/
    search.ts
    admin.ts
    analytics.ts
    auth.ts
```

`App.tsx` must not initialize theme state through an unconditional side effect on every render. Theme initialization belongs in a dedicated hook/effect or store initializer. `ProtectedRoute` checks authentication and role before rendering admin/analytics/settings content; it does not replace server-side authorization.

The URL is the canonical shareable state for `q`, filters, page, and `per_page`. The search store holds transient input, suggestion focus index, and recent local history. React Query owns request state and cache. Submission trims/validates a non-empty query, updates URL state with `replace` for typing and `push` for submit/navigation, invokes `useSearch` with typed `SearchParams`, renders loading without erasing the current query, then renders results, zero-result, or recoverable error state while retaining query context for click tracking.

Autocomplete is debounced and disabled below the configured minimum length. Arrow keys, Enter, Escape, and pointer selection share one selection model. Suggestions never replace the typed value without an explicit selection. React Query owns server state, invalidation, and polling; Zustand owns transient input, sidebar/theme/session UI state only. Admin mutations invalidate crawl/index/settings/API-key queries. Analytics supports date-range state, explicit loading/empty/error states, and optional stream updates.

The real-time stream is disabled by default. When enabled, an authenticated SSE/WebSocket client updates a small operational snapshot; it does not replace the authoritative analytics query. On disconnect it marks data stale, retries with backoff, and keeps the last successful snapshot available.

The existing Tailwind/theme intent is retained: JetBrains Mono for code/headings, IBM Plex Sans for body, Blue-700/Green-500/Slate light tokens, Slate-950/Slate-800/Blue-500/Green-500 dark tokens, and Lucide React icons. Components use semantic elements, labels, focus-visible styles, keyboard navigation, adequate contrast, responsive layouts, and reduced-motion support. Automated accessibility checks cover search, login, admin, and analytics pages; responsive visual checks cover mobile and desktop breakpoints. WCAG AA is a target validated by checks, not a claim inferred from CSS tokens alone.

## Data Models

### Durable PostgreSQL model

Existing Alembic revisions `001_initial_schema.py` and `002_add_pg_trgm_extension.py` remain the baseline and are reconciled with SQLAlchemy models before new feature migrations are added. The existing schema covers the following logical tables:

- `documents`: `id`, `url`, `canonical_url`, `content_hash`, `title`, `meta_description`, `headings`, `body_text`, `html_content`, `content_type`, `content_length`, `language`, `status_code`, `crawled_at`, `crawl_id`, `outlinks`, `inlinks_count`, `pagerank`, `created_at`, and `updated_at`.
- `inverted_index`: `term`, `document_id`, `field`, `frequency`, `positions`, and `tf_idf`.
- `term_stats`: `term`, `document_frequency`, `total_frequency`, `idf`, and `updated_at`.
- `crawl_jobs`: `id`, `name`, `seed_urls`, `allowed_domains`, `blocked_domains`, `max_depth`, `max_pages`, `max_pages_per_domain`, `crawl_delay`, `respect_robots_txt`, `user_agent`, `status`, `priority`, `pages_crawled`, `pages_failed`, `bytes_downloaded`, `started_at`, `completed_at`, `error_message`, `config`, `created_at`, and `updated_at`.
- `crawl_queue`: `id`, `crawl_job_id`, `url`, `normalized_url`, `domain`, `depth`, `priority`, `status`, `attempts`, `last_error`, `scheduled_at`, `crawled_at`, and `created_at`.
- `query_logs`: `id`, `query`, `normalized_query`, `corrected_query`, `results_count`, `page`, `per_page`, `search_time_ms`, `cache_hit`, `client_ip`, `user_agent`, `session_id`, `filters`, and `created_at`.
- `click_logs`: `id`, `query_log_id`, `document_id`, `position`, `dwell_time_ms`, and `created_at`.
- `admin_users`: `id`, `email`, `hashed_password`, `full_name`, `role`, `is_active`, `last_login`, `created_at`, and `updated_at`.
- `api_keys`: `id`, `name`, `key_hash`, `key_prefix`, `user_id`, `rate_limit`, `allowed_ips`, `is_active`, `expires_at`, `last_used_at`, and `created_at`.
- `settings`: `key`, `value`, `description`, `category`, `is_secret`, `updated_at`, and `updated_by`.
- An additive audit-event table is introduced if the baseline does not already provide durable audit storage.

Migration review explicitly verifies idempotent PostgreSQL extensions/indexes, upsert/idempotency constraints for `documents`, `crawl_queue`, `inverted_index`, and term statistics, click relationship integrity, application/database validation for status and role values, consistent timestamp/update semantics, documented array/JSONB representations in API schemas, and safe local-development downgrade behavior. Downgrade is not a production rollback strategy.

PostgreSQL’s `/docker-entrypoint-initdb.d` mechanism executes SQL/shell initialization files, not Python Alembic revision modules. The migration path is therefore:

1. PostgreSQL starts with only database/role initialization and a healthcheck.
2. A one-shot `migrate` profile/container runs `alembic upgrade head` after PostgreSQL readiness.
3. Application services depend on migration completion/readiness, or their entrypoint performs the same idempotent migration gate before starting.
4. Normal application startup never silently runs an arbitrary partial schema migration.
5. The documented clean-start workflow uses `docker compose up postgres redis rabbitmq`, `alembic upgrade head` locally or via the migration container, then application services.

A migration lock or single migration job prevents replicas from applying revisions simultaneously. The Compose file may retain an optional migration volume for development fixtures, but the Python revision directory is not mounted as PostgreSQL SQL init input.

Migration changes are additive and ordered: baseline validation/model drift correction; service-contract support columns/indexes such as correlation/audit identity or explicit document version; audit storage; optional analytics rollups/materialized views; optional stream/worker lease or dead-letter metadata; and demo-data indexes/constraints after functional paths are stable. No migration deletes existing data or renames a live column in place. Breaking schema changes use expand/backfill/contract with compatible fields and, when necessary, dual-read/dual-write before later cleanup. Demo fixtures and migration tests run against empty and existing baseline databases.

### Canonical identifiers and invariants

- URL identity is the normalized URL, with canonical URL used for document merge where present.
- Document identity is a UUID primary key; content hash detects unchanged content.
- Posting identity is `(term, document_id, field)`; positions and frequency are replaced on reindex.
- Query identity is a query-log UUID used internally for click context; clients receive an opaque query context token, not database internals.
- Message identity is a stable `event_id` and idempotency key in a versioned envelope.
- A repeated index task produces one logical document version, no duplicate posting key, and equivalent final term statistics.
- A crawler publishes an index event only after the document transaction commits.

### Text and search model

The positional inverted index stores `(doc_id, frequency, positions[], tf_idf, field)` per term. Fields use default weights of title `3.0`, heading `2.0`, body `1.0`, and anchor `1.5`; positions use gap encoding and document IDs use variable-byte compression where the implementation supports compression. Positional data enables phrase queries and proximity ranking. The Query Pipeline is:

1. Spell correction using edit distance and query-log frequency.
2. Tokenization and stemming.
3. Synonym expansion using WordNet when enabled.
4. Boolean parse for `+required`, `-excluded`, quoted phrases, `site:`, `filetype:`, `intitle:`, and `inurl:`.
5. Postings retrieval, BM25 scoring, feature merge, reranking, and pagination.

### Message model

RabbitMQ messages use durable topic exchanges and the versioned envelope described in **Components and Interfaces**. Every envelope has `event_id`, `event_type`, `schema_version`, `occurred_at`, `correlation_id`, `idempotency_key`, and a typed payload. Delivery is acknowledged only after durable effects commit. Malformed or exhausted work has a durable dead-letter record with failure details.

## Correctness Properties

*A correctness property is a behavior that must hold for all valid inputs or executions. Properties below are selected from the acceptance-criterion testability analysis; finite UI, infrastructure, documentation, and one-shot operational checks remain example, integration, smoke, or end-to-end tests rather than forced property tests.*

### Property 1: Contract-complete search responses

For any valid search query, pagination values, and supported filters, the Search API response contains the normalized query, optional correction, result collection, total count, bounded pagination metadata, elapsed time, cache status, and a stable query context; for any invalid input, it returns the common error shape with a validation code.

**Validates: Requirements 2.2, 2.7**

### Property 2: Bounded typed suggestions

For any partial query and configured valid limit, every returned suggestion has a non-empty type, suggestions are in deterministic configured order, and the number of suggestions is no greater than the effective limit.

**Validates: Requirements 2.3**

### Property 3: URL policy and duplicate elimination

For any URL and crawl policy, normalization produces one stable identity; any invalid, blocked, out-of-policy, or robots-disallowed URL is recorded as rejected and is never included in the fetch set, while normalized duplicates map to one frontier identity.

**Validates: Requirements 3.4**

### Property 4: Bounded crawler retry state machine

For any sequence of retryable and terminal fetch outcomes and any configured attempt/backoff limits, the crawler retries only retryable outcomes within the configured bounds, schedules retryable attempts with bounded backoff, and persists one terminal failure after exhaustion without losing the queue entry’s final reason.

**Validates: Requirements 3.5**

### Property 5: HTML extraction preserves required document facts

For any accepted HTML document containing arbitrary supported titles, metadata, headings, body text, canonical URL, and links, extraction returns normalized text and metadata, a deterministic content hash, a language/content field, and normalized outlinks without including configured non-content elements.

**Validates: Requirements 3.6**

### Property 6: Index postings and statistics match the document model

For any valid document collection and configured text-processing policy, tokenization and indexing produce repeatable positional postings whose frequencies and positions match the processed fields, and term statistics report the corresponding document frequency, total frequency, and IDF values.

**Validates: Requirements 4.1, 4.2**

### Property 7: Index delivery is idempotent

For any valid index task, applying the task once or applying the same task repeatedly produces one logical document version, at most one posting for each `(term, document, field)` key, and equivalent term statistics after the final commit.

**Validates: Requirements 3.7, 4.3**

### Property 8: BM25 agrees with the configured reference formula

For any generated corpus, query terms, field frequencies, document lengths, and valid ranking configuration, the Ranker’s BM25 score equals the direct configured BM25 calculation within the documented floating-point tolerance and applies the configured field weights.

**Validates: Requirements 4.4**

### Property 9: PageRank graph invariants

For any finite directed document graph, including graphs with dangling nodes, PageRank computation terminates within the configured iteration bound, applies the configured dangling-node policy and damping, produces non-negative normalized scores, and persists one score per participating document.

**Validates: Requirements 4.5**

### Property 10: Configured score composition

For any candidate feature vector and valid operational ranking configuration, changing a signal changes the final score only according to its configured weight, disabled signals have no effect, and the combined score is the configured composition of lexical, authority, freshness, phrase, prefix, and diversification inputs.

**Validates: Requirements 4.6**

### Property 11: Query pipeline stage invariants

For any supported query syntax and indexed corpus, normalization precedes parsing, parsing determines retrieval/filter constraints, ranking is applied only to retrieved candidates, snippets/highlights refer to returned documents, and pagination returns a disjoint ordered slice whose count metadata describes the unpaginated result set.

**Validates: Requirements 4.7**

### Property 12: Empty-result responses are successful and honest

For any normalized query with no matching candidate documents, the Search API returns a successful response with zero results and zero total count, preserves the normalized query, and includes only actually available correction or suggestion information.

**Validates: Requirements 4.8, 7.3**

### Property 13: Permission matrix is enforced consistently

For any administrative endpoint and any principal state, a missing or invalid principal receives `401`, an active principal lacking the endpoint permission receives `403`, and a principal with the required role can execute only the operations allowed by the central RBAC matrix.

**Validates: Requirements 6.4, 6.5, 6.6**

### Property 14: Configuration is validated and redacted

For any supported configuration override set, valid values produce an effective configuration with documented defaults and overrides, invalid connection/security/range values fail before service readiness, and effective-config logs never contain passwords, tokens, private keys, or API-key material.

**Validates: Requirements 8.1, 8.2, 8.6**

### Property 15: Transient dependency loss does not duplicate durable work

For any bounded sequence of transient PostgreSQL, Redis, RabbitMQ, or downstream HTTP failures and duplicate delivery attempts, the affected component retries or reconnects within policy, either commits one idempotent result or records a durable terminal failure, and never acknowledges work before its durable side effect completes.

**Validates: Requirements 8.4, 4.3**

### Property 16: Demo loading is deterministic and repeatable

For any clean or already-loaded migrated demo database, running the offline demo loader produces the same logical fixture identities and complete category set; repeated runs change only inserted/skipped/updated counters and do not create duplicate documents, postings, logs, or suggestions.

**Validates: Requirements 9.1, 9.2**

### Property 17: Analytics aggregation reflects available samples

For any generated query/click log set and requested time range, analytics counts only records in range, computes each supported metric from available samples, preserves filter dimensions, and returns explicit empty/unavailable values when no sample supports a metric rather than fabricating a value.

**Validates: Requirements 7.1, 7.2, 7.3**

### Property 18: Validation preserves diagnostic truth

For any validation run containing passing, failing, unavailable-dependency, and optional-benchmark cases, the summary reports each failure with test/layer/service/dependency context, distinguishes functional results from known limitations, and marks absent benchmark infrastructure as unmeasured rather than passing.

**Validates: Requirements 10.4, 10.5, 10.6, 10.7**

## Error Handling

### Common HTTP errors and health behavior

Stable errors use this shape:

```json
{
  "error": {
    "code": "SEARCH_INVALID_QUERY",
    "message": "Query must contain at least one searchable character",
    "details": {},
    "request_id": "uuid"
  }
}
```

`details` is safe structured context and never includes secrets, raw credentials, or sensitive database errors. Validation is `422`, unauthenticated is `401`, unauthorized is `403`, not-found is `404`, rate-limited is `429`, dependency failure is `502`, dependency timeout is `504`, and unexpected service failure is `500` with a generic message. Downstream failures are logged with the propagated correlation identifier.

Health and readiness use:

```json
{
  "service": "search-api",
  "status": "ready",
  "version": "git-or-image-version",
  "dependencies": {
    "postgres": {"status": "ready", "latency_ms": 2},
    "redis": {"status": "ready", "latency_ms": 1},
    "ranker": {"status": "ready", "latency_ms": 4}
  },
  "request_id": "uuid"
}
```

`/health/live` checks process liveness. `/health/ready` checks required dependencies and returns non-ready status without claiming the service can serve traffic. All gateway, Search API, Crawler, Indexer, Ranker, and Admin API services expose these endpoints with service/version/request-ID fields.

### Startup, dependency, and worker failures

Startup failures identify the service, dependency, failure class, and remediation, for example: `search-api cannot connect to postgres: connection refused; verify DATABASE_URL and that postgres is healthy`. Required dependencies use bounded startup retries. A service that cannot connect reports the dependency instead of starting in a falsely ready state.

HTTP downstream calls use explicit connect/read/total timeouts and bounded retries only for safe/idempotent operations, with circuit-breaker or open-failure state where repeated outages would amplify load. PostgreSQL uses bounded reconnect/startup retry; transaction failures are surfaced rather than partially acknowledged. Redis is non-authoritative: cache/live-snapshot failures degrade to uncached/stale operation where safe. RabbitMQ uses bounded reconnect/backoff, durable queues, publisher confirms, consumer acknowledgement after commit, and dead-letter routing after maximum delivery attempts.

Crawler retries only configured transient HTTP/error classes and persists final failure. Duplicate HTTP commands and message deliveries use idempotency keys and legal state transitions. Worker shutdown stops accepting work, finishes or negatively acknowledges in-flight work according to policy, and closes clients within the grace period without claiming uncommitted work succeeded.

### Crawler and pipeline failure behavior

Invalid, blocked, duplicate, out-of-domain, and robots-disallowed URLs are recorded with a rejection reason and never fetched. Retryable `429`/`5xx` and configured transient errors are retried only within attempt and backoff limits; exhausted retries persist one final failure reason. Invalid content type, oversized response, redirect-limit, and malformed HTML cases are terminal or controlled extraction failures according to crawler configuration.

Crawler documents are durable before index events are published. Indexer messages are acknowledged only after postings and statistics commit. Malformed or exhausted index messages are routed to `document.index.dead-letter` with failure details. Repeated tasks update existing logical records rather than producing duplicate postings.

When Ranker is unavailable or times out, Search API returns the documented `502`/`504` error or a configured bounded lexical-only response. It never waits indefinitely. When no documents match, Search API returns a successful empty response with normalized query and only available correction/suggestion data. Click logging is non-blocking; a click persistence failure does not prevent browser navigation.

### Authentication, security, and configuration failures

Invalid credentials, inactive accounts, expired/malformed tokens, wrong refresh-token types, and missing authentication use safe documented errors and do not disclose whether a credential or account lookup failed. Missing authentication is `401`; insufficient privilege is `403`. API-key plaintext is returned only at creation, never logged or returned later; inactive, expired, revoked, or disallowed-IP keys fail authentication and do not update last-use metadata.

Configuration validation rejects invalid URLs, ports, ranges, timeouts, origins, weights, connection values, and production security settings before readiness. Development defaults are labeled development-only. Production mode refuses placeholder/weak JWT secrets and requires explicit production values. Effective configuration and diagnostics redact passwords, tokens, private keys, API keys, and other key material.

Gateway/Nginx policy rejects or limits requests according to configured body size, connection limits, CORS, rate limits, security headers, trusted proxies, and protected direct-service access. Nginx is an edge layer, not a substitute for JWT/RBAC. TLS certificate paths, secure headers/cookies, trusted proxy behavior, metrics access, and health endpoint exposure are documented for external deployment.

## Testing Strategy

The test suite is layered and does not silently skip a failed dependency or fixture. Unit tests verify pure logic and representative examples; property tests verify universal behavior; integration tests verify persistence and service boundaries; end-to-end tests verify the Compose/browser workflow; and optional benchmark tests report goals only when measured.

### Unit and property layer

Pure modules are tested without network or cloud dependencies:

- URL normalization/filtering and domain policy;
- HTML extraction and content hashing;
- tokenization, stopwords, stemming, positions, and field extraction;
- query parser/operators and snippet/highlight generation;
- BM25, score combination, diversification, and PageRank reference comparisons;
- frontier ordering, retry/backoff state machines, and politeness decisions;
- rate limiting, configuration validation, and error mapping;
- password/token validation and the RBAC permission matrix.

Property-based tests use at least 100 generated cases per property. Each property test carries the feature/property tag in the test name or marker, for example: `Feature: complete-search-engine-project, Property 4: Bounded crawler retry state machine`. Property tests are limited to project-owned pure logic or mocked durable-work models; UI rendering, infrastructure wiring, external services, and one-shot configuration checks use the other layers below.

### Integration layer

Disposable PostgreSQL, Redis, and RabbitMQ fixtures verify:

- migration from empty and baseline databases;
- Search API with seeded documents, postings, cache, and logs;
- crawler frontier, document persistence, and controlled HTTP fixtures;
- crawler-to-indexer message delivery and dead-letter behavior;
- indexer postings/statistics and Ranker data flow;
- Admin API CRUD, authentication, RBAC, API-key lifecycle, audit, and analytics aggregation;
- health/readiness and dependency failure mappings;
- gateway routing, timeout/error mapping, and Nginx/application policy parity.

Integration tests use real protocol clients and controlled HTTP fixtures, not external websites. They report service, layer, dependency, and fixture context for every failure.

### End-to-end layer

Compose-backed browser/system tests verify startup readiness, login, search, autocomplete, URL state, result click logging, crawl control, analytics rendering, optional stream behavior, unknown-route fallback, and recoverable Search API/suggestion failure. The suite captures gateway/service logs by request ID and fails explicitly when a dependency or fixture is unavailable.

Frontend component and accessibility tests cover route rendering, URL state, loading/error/empty states, suggestion selection, click tracking, keyboard navigation, theme behavior, focus visibility, semantic accessible names, and responsive desktop/mobile breakpoints. Zero-result UI and auth-failure recovery are tested as explicit edge scenarios.

### Benchmark layer

Benchmark Infrastructure is optional and separate from functional validation. A Locust or equivalent harness runs repeatable scenarios for search, autocomplete, and crawl throughput. Reports include environment, dataset size, concurrency, throughput, error rate, p50/p95/p99, and comparison with the implementation-plan goals:

- search: 1,000 requests/second and p99 below 200 ms;
- autocomplete: 500 requests/second and p99 below 50 ms;
- crawl: 1,000 pages/minute.

If the harness or required environment is unavailable, the validation summary explicitly reports these goals as **unmeasured**, never as passing or failing performance claims. The summary includes test name, layer, service, dependency, fixture, failure reason, known limitations, functional pass/fail state, and benchmark measurement status.
