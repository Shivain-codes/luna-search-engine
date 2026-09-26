# Luna - Complete Implementation Plan

## Project Overview
Building a production-quality search engine from scratch (CS50 Final Project + Google STEP portfolio). Demonstrates: Algorithms, Data Structures, Graph Theory, Information Retrieval, Databases, Networking, Software Architecture, Full-Stack Development.

---

## Tech Stack
- **Backend**: Python 3.13, FastAPI, SQLAlchemy 2.0, PostgreSQL 16, Alembic, Pydantic v2
- **Frontend**: React 18, TypeScript, Vite, Tailwind CSS, Framer Motion, React Query, React Router
- **Search/IR**: BeautifulSoup, Requests, NLTK, Custom Inverted Index, BM25, PageRank
- **Infrastructure**: Docker, Redis, RabbitMQ, Pytest

---

## Architecture: Microservices with Clean Architecture

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌──────────┐
│   FRONTEND  │◄──▶│  API GATEWAY │◄──▶│  SEARCH API │◄──▶│  RANKER  │
│  (React/TS) │    │  (FastAPI)  │    │  (FastAPI)  │    │ (Python) │
└─────────────┘    └─────────────┘    └──────┬──────┘    └──────────┘
                                             │
                    ┌────────────────────────┼────────────────────────┐
                    │                        │                        │
                    ▼                        ▼                        ▼
             ┌─────────────┐          ┌─────────────┐          ┌─────────────┐
             │   CRAWLER   │          │   INDEXER   │          │  ADMIN API  │
             │  (Python)   │          │  (Python)   │          │  (FastAPI)  │
             └──────┬──────┘          └──────┬──────┘          └─────────────┘
                    │                        │
                    ▼                        ▼
             ┌─────────────────────────────────────────────┐
             │              INFRASTRUCTURE                  │
             │  PostgreSQL  │  Redis  │  RabbitMQ  │  Nginx │
             └─────────────────────────────────────────────┘
```

---

## Service Specifications

### 1. API Gateway (Port 8000)
- Routes requests to Search API / Admin API
- JWT authentication, rate limiting, CORS
- Request/response logging, health checks

### 2. Search API (Port 8001)
- **GET /api/v1/search** - Main search endpoint
  - Query params: `q`, `page`, `per_page`, `site`, `language`, `safe_search`, `date_range`
  - Returns: results with snippets, highlighting, pagination, search_time_ms
- **GET /api/v1/suggest** - Autocomplete
  - Query params: `q`, `limit`
  - Returns: suggestions with types (query/site/entity)

### 3. Crawler Service (Port 8002)
- **POST /api/v1/crawl/jobs** - Create crawl job
- **GET /api/v1/crawl/jobs** - List jobs
- **PATCH /api/v1/crawl/jobs/{id}** - Pause/resume/cancel
- **GET /api/v1/crawl/queue/stats** - Queue depth, domain stats
- Features: robots.txt compliance, per-domain rate limiting, deduplication, polite crawling

### 4. Indexer Service (Port 8003)
- Consumes crawl results from RabbitMQ
- HTML parsing → text extraction → tokenization → stemming → inverted index
- Computes TF-IDF, stores positions for phrase queries
- Updates term statistics (DF, IDF)

### 5. Ranker Service (Port 8004)
- **POST /api/v1/rank/score** - Score documents for query
- BM25 + PageRank + Title/Heading/URL boosts
- Periodic PageRank computation on link graph
- Feature extraction for future LTR

### 6. Admin API (Port 8005)
- Crawl job management, index stats, analytics
- Query logs, zero-result queries, latency percentiles
- Ranking weight tuning, API key management

### 7. Frontend (Port 3000)
- **Search Page**: Hero search bar, autocomplete, results with snippets, pagination/infinite scroll
- **Admin Dashboard**: Crawl control, real-time charts (Recharts), index stats, query analytics
- **Analytics Dashboard**: Query volume, CTR, latency, geo, zero-results analysis
- Dark/light mode, responsive, accessible (WCAG AA)

---

## Database Schema (PostgreSQL)

### Core Tables
```sql
-- Documents (crawled pages)
documents: id, url, canonical_url, content_hash, title, meta_description,
           headings, body_text, html_content, content_type, content_length,
           language, status_code, crawled_at, crawl_id, outlinks[],
           inlinks_count, pagerank, created_at, updated_at

-- Inverted Index (term → doc mappings)
inverted_index: term, document_id, field, frequency, positions[], tf_idf
term_stats: term, document_frequency, total_frequency, idf, updated_at

-- Crawling
crawl_jobs: id, name, seed_urls[], allowed_domains[], blocked_domains[],
            max_depth, max_pages, max_pages_per_domain, crawl_delay,
            respect_robots_txt, user_agent, status, priority,
            pages_crawled, pages_failed, bytes_downloaded, started_at,
            completed_at, error_message, config, created_at, updated_at
crawl_queue: id, crawl_job_id, url, normalized_url, domain, depth, priority,
             status, attempts, last_error, scheduled_at, crawled_at, created_at

-- Analytics
query_logs: id, query, normalized_query, corrected_query, results_count,
            page, per_page, search_time_ms, cache_hit, client_ip, user_agent,
            session_id, filters, created_at
click_logs: id, query_log_id, document_id, position, dwell_time_ms, created_at

-- Admin
admin_users: id, email, hashed_password, full_name, role, is_active,
             last_login, created_at, updated_at
api_keys: id, name, key_hash, key_prefix, user_id, rate_limit,
          allowed_ips[], is_active, expires_at, last_used_at, created_at
settings: key, value, description, category, is_secret, updated_at, updated_by
```

---

## Key Algorithms & Data Structures

### Inverted Index
- **Postings Lists**: `(doc_id, frequency, positions[], tf_idf, field)` per term
- **Fields**: title (weight 3.0), heading (2.0), body (1.0), anchor (1.5)
- **Compression**: Gap encoding for positions, variable-byte for doc_ids
- **Positional Index**: Enables phrase queries, proximity ranking

### BM25 Scoring
```
score = Σ IDF(q) * (f(q,D) * (k1 + 1)) / (f(q,D) + k1 * (1 - b + b * |D|/avgdl))
k1=1.5, b=0.75
IDF = log((N - df + 0.5) / (df + 0.5) + 1)
```

### PageRank
- Power iteration on link graph (dangling node handling)
- Damping factor 0.85, 30 iterations, tolerance 1e-6
- Stored in `documents.pagerank`, updated weekly

### Query Processing Pipeline
1. Spell correction (edit distance + query log frequency)
2. Tokenization + stemming
3. Synonym expansion (WordNet)
4. Boolean parse (+required -excluded "phrase" site: filetype: intitle: inurl:)
5. Postings retrieval → BM25 scoring → Feature merge → Rerank → Paginate

---

## Crawler Implementation Details

### Politeness Manager
```python
class PolitenessManager:
    - Per-domain token bucket (rate = 1/crawl_delay)
    - Robots.txt cache with TTL (24h)
    - Concurrent request limiter per domain (max 2)
    - Global concurrent limiter (max 50)
    - Exponential backoff on 429/5xx
```

### URL Frontier
- Priority queue: (priority, scheduled_at, url)
- Priority: seed=100, internal links=50, external=10
- Deduplication via normalized URL hash (SHA256)
- Depth tracking, per-domain page limits

### Content Extraction
- Remove: script, style, noscript, iframe, svg, canvas, header, footer, nav, aside
- Extract: title, meta description, Open Graph, JSON-LD schema
- Headings hierarchy (h1-h6)
- Clean text: normalize whitespace, decode entities
- Language detection (fasttext)

---

## Frontend Components (React + TypeScript)

### Design System
- **Fonts**: JetBrains Mono (code/headings) + IBM Plex Sans (body)
- **Colors Light**: Blue-700 primary, Green-500 accent, Slate-50 bg, Slate-900 text
- **Colors Dark**: Slate-950 bg, Slate-800 surface, Blue-500 primary, Green-500 accent
- **Icons**: Lucide React (consistent, tree-shakable)

### Core Components
```
components/
├── ui/                    # Primitives
│   ├── Button, Input, Card, Badge, Avatar, Dropdown, Modal
│   ├── Skeleton, Spinner, Tooltip, Toaster
├── search/
│   ├── SearchHero         # Centered search bar with autocomplete
│   ├── SearchResults      # List with highlighting, cached links
│   ├── ResultCard         # Title, URL, snippet, actions
│   ├── Pagination         # Page numbers + infinite scroll toggle
│   ├── NoResults          # Friendly message + suggestions
├── admin/
│   ├── Sidebar            # Collapsible navigation
│   ├── KPICard            # Metric with trend
│   ├── CrawlJobTable      # Status badges, actions
│   ├── QueueDepthChart    # Real-time area chart
├── analytics/
│   ├── QueryVolumeChart   # Time series with annotations
│   ├── TopQueriesTable    # Sortable, clickable
│   ├── ZeroResultsTable   # With suggested fixes
│   ├── LatencyPercentiles # p50/p95/p99 lines
├── layout/
│   ├── Navbar             # Logo, tabs, theme toggle, user menu
│   ├── Footer             # Links, version, stats
```

### State Management
- **React Query**: Server state (search, analytics, admin)
- **Zustand**: UI state (theme, sidebar, search history)
- **URL State**: Search params in URL for shareability

---

## Docker Compose Services

```yaml
services:
  postgres:     # Port 5432, healthcheck pg_isready
  redis:        # Port 6379, maxmemory 512mb, LRU
  rabbitmq:     # Ports 5672, 15672 (management)
  api-gateway:  # Port 8000, replicas=2
  search-api:   # Port 8001, replicas=2
  crawler:      # replicas=3
  indexer:      # replicas=2
  ranker:       # Port 8004
  admin-api:    # Port 8005
  frontend:     # Port 3000
```

---

## Testing Strategy

### Unit Tests (pytest)
- Tokenizer, stemmer, URL normalizer
- BM25 scorer, PageRank calculator
- Query parser (boolean, phrases, operators)
- Rate limiter, auth middleware

### Integration Tests
- Search API with seeded database
- Crawler → Indexer → Ranker pipeline
- Admin API CRUD operations

### Load Tests (Locust)
- Search: 1000 req/s, p99 < 200ms
- Autocomplete: 500 req/s, p99 < 50ms
- Crawl throughput: 1000 pages/min

---

## Implementation Order

### Phase 1: Foundation (Week 1)
1. Project scaffolding, Docker Compose, shared library
2. Database models, migrations, connection pooling
3. RabbitMQ client, queue definitions
4. Configuration system, logging, health checks

### Phase 2: Core Search (Week 2)
5. Inverted index builder (Indexer service)
6. BM25 + PageRank (Ranker service)
7. Search API with query parsing, scoring, pagination
8. Autocomplete with Redis-backed suggestions

### Phase 3: Crawler (Week 3)
9. Polite HTTP client with aiohttp
10. Robots.txt parser (reppy)
11. URL frontier with priority queue
12. Content extraction pipeline
13. Crawl job management API

### Phase 4: Frontend (Week 4)
14. Vite + React + TypeScript + Tailwind setup
15. Design system components
16. Search page with autocomplete, results, pagination
17. Dark/light mode, responsive design

### Phase 5: Admin & Analytics (Week 5)
18. Admin API with auth, RBAC
19. Admin dashboard with charts (Recharts)
20. Analytics pipeline (query logs → aggregations)
21. Real-time metrics via WebSocket/SSE

### Phase 6: Polish (Week 6)
22. E2E tests, load tests, performance tuning
23. Documentation (API, architecture, deployment)
24. Demo data seeding, portfolio presentation prep
25. Production deployment config

---

## File Structure

```
search-engine/
├── docker-compose.yml
├── .env.example
├── Makefile
├── README.md
├── SPEC.md
├── IMPLEMENTATION_PLAN.md
├── docs/
│   ├── architecture.md
│   ├── api.md
│   └── deployment.md
├── config/
│   ├── crawler.yaml
│   ├── ranking.yaml
│   └── nginx.conf
├── migrations/
│   └── versions/
├── scripts/
│   ├── seed_demo_data.py
│   ├── run_crawler.py
│   ├── compute_pagerank.py
│   └── benchmark_search.py
├── shared/
│   └── python/
│       └── luna_shared/
│           ├── __init__.py
│           ├── config.py
│           ├── database.py
│           ├── models/
│           │   ├── __init__.py
│           │   ├── document.py
│           │   ├── inverted_index.py
│           │   ├── crawl_job.py
│           │   ├── analytics.py
│           │   └── admin.py
│           ├── utils/
│           │   ├── __init__.py
│           │   ├── text_processing.py
│           │   └── url.py
│           ├── messaging/
│           │   ├── __init__.py
│           │   ├── rabbitmq.py
│           │   └── queue_names.py
│           └── security/
│               ├── __init__.py
│               ├── auth.py
│               └── rate_limit.py
├── services/
│   ├── api-gateway/
│   ├── search-api/
│   ├── crawler/
│   ├── indexer/
│   ├── ranker/
│   └── admin-api/
│       Each with: Dockerfile, pyproject.toml, src/, tests/
└── frontend/
    ├── package.json
    ├── tsconfig.json
    ├── vite.config.ts
    ├── tailwind.config.js
    ├── postcss.config.js
    ├── index.html
    ├── public/
    └── src/
        ├── main.tsx
        ├── App.tsx
        ├── styles/
        │   ├── globals.css
        │   └── theme.css
        ├── components/
        │   ├── ui/
        │   ├── search/
        │   ├── results/
        │   ├── admin/
        │   ├── analytics/
        │   └── layout/
        ├── pages/
        │   ├── SearchPage.tsx
        │   ├── ResultsPage.tsx
        │   ├── AdminDashboard.tsx
        │   ├── AnalyticsDashboard.tsx
        │   └── SettingsPage.tsx
        ├── hooks/
        │   ├── useSearch.ts
        │   ├── useAutocomplete.ts
        │   ├── useTheme.ts
        │   └── useDebounce.ts
        ├── services/
        │   ├── api.ts
        │   └── analytics.ts
        ├── store/
        │   ├── searchStore.ts
        │   ├── themeStore.ts
        │   └── adminStore.ts
        ├── types/
        │   ├── search.ts
        │   ├── admin.ts
        │   └── analytics.ts
        └── utils/
            ├── formatting.ts
            └── constants.ts
```

---

## Portfolio Talking Points

1. **Custom Inverted Index**: Built from scratch in PostgreSQL with positional data, TF-IDF, field weights
2. **BM25 + PageRank**: Implemented classic IR ranking with link analysis
3. **Distributed Crawler**: Polite, concurrent, respects robots.txt, handles 1000s pages/min
4. **Clean Architecture**: Domain-driven, dependency inversion, testable services
5. **Full-Stack**: React/TypeScript frontend with real-time admin dashboards
6. **Production Ready**: Docker, health checks, rate limiting, auth, monitoring hooks
7. **Scale Design**: Stateless services, partitioned queues, Redis caching, read replicas ready

---

## Demo Data
- Seed: Wikipedia, GitHub, MDN, Stack Overflow, major tech blogs
- Target: ~100K indexed pages for demo
- Pre-computed PageRank, cached autocomplete

---

## Next Steps for Implementation

Run this plan through the implementation agent with:
```
"Build the complete Luna project per IMPLEMENTATION_PLAN.md. Start with Phase 1 foundation: Docker Compose, shared library, database models, migrations. Then proceed through each phase sequentially."
```