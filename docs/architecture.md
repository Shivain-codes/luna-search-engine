# Architecture

## Runtime topology

```
Browser
   │
   ▼
API Gateway :8000 ── public /api/v1/search, /suggest, /clicks ──▶ Search API :8001 ──▶ Ranker :8004
   │                                                                     │
   └── auth + /api/v1/admin/* ──▶ Admin API :8005                        ├─▶ PostgreSQL
   │                                                                     └─▶ Redis (cache)
   └── Redis (rate limits)

Crawler workers ──▶ RabbitMQ (document.index.requested) ──▶ Indexer workers ──▶ PostgreSQL
```

External clients only ever talk to the gateway. Service-to-service calls use
container/service names on the Compose network.

## Services

| Service | Port | Owns |
|---|---|---|
| api-gateway | 8000 | Public ingress, routing, per-endpoint rate limiting, CORS, request-id propagation, downstream error mapping |
| search-api | 8001 | Query normalization/parsing, retrieval, ranking (via ranker or local fallback), snippets, pagination, caching, query/click logging |
| crawler | 8002 | Frontier management, robots/politeness, fetching, extraction, document upsert, index-task publication |
| indexer | 8003 | Consume index tasks, tokenize/stem, build positional postings, maintain term statistics |
| ranker | 8004 | Field-aware BM25 scoring, PageRank computation and persistence |
| admin-api | 8005 | Auth, RBAC, crawl control, index stats, analytics, settings, API keys, audit |

## Data flow: crawl → index → rank → search

1. **Crawl.** `CrawlService.process_next` pulls the highest-priority pending URL
   from `crawl_queue`, applies URL policy and robots rules, fetches with
   politeness controls, extracts content, upserts a `Document`, enqueues
   discovered links, and — after the DB commit — publishes an
   `document.index.requested` envelope with idempotency key `docid:contenthash`.
2. **Index.** `index_document` loads the document, rebuilds positional postings
   for each field, replaces prior postings transactionally (idempotent), and
   updates `term_stats` (document frequency + IDF).
3. **Rank.** The search API retrieves candidate documents by term, then asks the
   ranker to score them (field-weighted BM25 + PageRank + freshness). If the
   ranker is unavailable it falls back to local BM25 scoring.
4. **Serve.** Results are filtered, snippet-highlighted, paginated, cached in
   Redis (when eligible), and returned with an opaque `query_context`. The query
   is logged; clicks reference the context for analytics.

## Shared library

`shared/python/luna_shared/`:

- `ir/` — `bm25.py`, `pagerank.py`, `query.py`, `extraction.py`, `indexing.py`,
  `scoring.py` (the original IR algorithms).
- `models/` — SQLAlchemy models (documents, inverted_index, term_stats,
  crawl_jobs, crawl_queue, query_logs, click_logs, audit_events, admin_users,
  api_keys, settings).
- `repositories/` — async data-access classes.
- `security/` — password hashing, JWT, RBAC matrix, rate limiting.
- `app.py` — FastAPI factory with health endpoints and middleware.
- `config.py` — typed settings with per-service subclasses and secret redaction.

## Portability

The data layer runs on PostgreSQL and SQLite from one set of models via
dialect-adaptive column types. Redis and RabbitMQ each have an in-memory backend
(`memory://`) so the full stack runs without external infrastructure for local
development and testing. Production uses Postgres + Redis + RabbitMQ through
Docker Compose.

## Algorithms

- **BM25:** `IDF·tf·(k1+1) / (tf + k1·(1 - b + b·|field|/avgFieldLen))`,
  summed across weighted fields. `k1=1.5`, `b=0.75`.
- **PageRank:** power iteration, damping 0.85, dangling-node redistribution,
  normalized scores.
- **Combined score:** `w_bm25·BM25 + w_pr·PageRank + w_fresh·freshness`, weights
  from `config/ranking.yaml`.
- **Text analysis:** Unicode normalization, tokenization, stopword removal, and
  a from-scratch Porter stemmer.
