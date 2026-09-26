# Luna — Design

This document explains the design of Luna: what I built, the choices I
made, and why. It is written as the design writeup for a CS50 final project.

## Overview

Luna is a working search engine. Rather than call an existing search
library, I implemented the core information-retrieval machinery myself — the
inverted index, the BM25 ranking function, and the PageRank algorithm — so the
project demonstrates the underlying computer science, not just API glue.

The system is organized as six small backend services and a React frontend.
That separation mirrors how real search systems are built (crawling, indexing,
ranking, and serving are independent concerns) and made each piece easy to
test in isolation.

## The information-retrieval core

All of the interesting algorithms live in `shared/python/luna_shared/ir/`.

### Inverted index

The index maps each **term** to the documents that contain it. For every
`(term, document, field)` I store the term frequency and the list of token
**positions**. Positions make phrase and proximity matching possible later.
Fields (title, headings, body, metadata, URL) are indexed separately so the
ranker can weight a title match more heavily than a body match.

Term statistics (document frequency and IDF) are maintained globally so scoring
does not have to scan the whole corpus per query.

### BM25 ranking

BM25 is the standard bag-of-words relevance function. For a query term in a
document field:

```
score = IDF(term) · tf·(k1+1) / (tf + k1·(1 - b + b·|field|/avgFieldLen))
```

with `k1 = 1.5`, `b = 0.75`. IDF uses the usual `log((N - df + 0.5)/(df + 0.5) + 1)`
smoothing. I sum the contribution across fields, each multiplied by a field
weight (title 3.0, heading 2.0, body 1.0, …). I wrote a property-based test
(Hypothesis) that generates random corpora and asserts my score equals a direct
evaluation of the formula, which caught two normalization bugs early.

### PageRank

PageRank measures page authority from the link graph. I implemented power
iteration with a damping factor of 0.85, dangling-node mass redistribution, and
a convergence tolerance. The result is normalized so scores sum to 1. Property
tests assert the invariants (non-negative, sums to 1, terminates) for arbitrary
graphs including graphs with dangling nodes.

The final ranking blends BM25 (relevance), PageRank (authority), and freshness
with configurable weights from `config/ranking.yaml`.

### Query processing

Queries are normalized (Unicode, whitespace, case) and parsed into required
terms, excluded terms (`-term`), exact phrases (`"…"`), and field operators
(`site:`, `intitle:`, `inurl:`). Terms are stemmed with a from-scratch Porter
stemmer so `running` and `runs` match `run`.

## The crawler

The crawler is deliberately polite, because a rude crawler is a broken crawler.
It maintains a URL frontier as a priority queue in the database, respects
`robots.txt` (cached with a TTL), rate-limits per domain with a token-bucket
style delay, limits global and per-domain concurrency, and retries transient
failures with bounded exponential backoff. Content extraction strips scripts,
styles, and navigation chrome before storing clean text.

A subtle but important correctness rule: the crawler publishes an "index this
document" message **only after** the document transaction commits, and index
messages carry an idempotency key (`document_id:content_hash`). This means a
duplicate delivery re-indexes the same document rather than creating duplicates.

## Data layer and a key portability decision

Everything durable lives in PostgreSQL. The biggest practical design decision
was making the data layer **portable**: the same models and repositories run on
PostgreSQL in production and on SQLite for local development and tests, and the
cache and message broker each have an in-memory backend selected by URL
(`memory://`). This means the entire system — crawl, index, rank, search — runs
and is fully testable with **no external infrastructure at all**, which made
development and grading dramatically easier while keeping the production path
(Postgres + Redis + RabbitMQ via Docker Compose) intact.

Portable column types (JSON that becomes JSONB on Postgres, a UUID type that
adapts per dialect) let one set of models serve both databases. Migrations are
generated directly from the model metadata so the schema and the code can never
drift.

## Services and boundaries

- **api-gateway** is the only public entry point. It routes, rate-limits, adds
  request IDs, and maps downstream failures to clean 502/504 errors.
- **search-api** owns the query pipeline and calls the ranker over HTTP, with a
  local BM25 fallback so search still works if the ranker is down.
- **crawler** and **indexer** are asynchronous workers connected by RabbitMQ.
- **ranker** is pure computation (BM25/PageRank) with no presentation logic.
- **admin-api** owns authentication, RBAC, and all administrative operations.

The shared library holds only cross-cutting code (models, IR algorithms, data
access, security). Business logic lives in the service that owns it.

## Security

Passwords are hashed with scrypt (standard library, no native build needed).
Access and refresh tokens are JWTs with issuer/audience/type claims and expiry.
Authorization is a central role/permission matrix (`viewer`, `operator`,
`admin`) enforced by FastAPI dependencies — the API returns 401 without a valid
token and 403 without the required permission. API keys are shown once on
creation and only a hash is stored. Administrative actions are written to an
audit log.

## Frontend

The UI is a React + TypeScript SPA. Search state lives in the URL so results are
shareable and the back button works. Autocomplete is debounced and fully
keyboard-navigable. The admin and analytics dashboards use React Query for server
state with cache invalidation after mutations, and Recharts for visualization.
The app targets WCAG AA (semantic markup, focus states, labels, contrast) and
supports light/dark themes.

## Testing

I test at three levels: unit tests for pure functions (stemming, BM25, URL
normalization), property-based tests for the algorithms (BM25 vs. the reference
formula, PageRank invariants), and integration tests that exercise the full
crawl→index→rank→search pipeline and the admin API (auth, RBAC, CRUD) through a
real HTTP test client. The suite runs entirely on SQLite in about a second.

## What I would do next

- Learning-to-rank on top of the current features.
- Real-time analytics over WebSocket/SSE (scaffolded but disabled by default).
- A benchmark harness run on real infrastructure to measure the throughput and
  latency goals, which today remain design targets rather than measured numbers.

## Why these choices

I optimized for **demonstrating the computer science** and for a system that
anyone can run in one command. Implementing BM25 and PageRank myself, keeping
the services honestly separated, and making the whole thing runnable on SQLite
with in-memory infrastructure were the decisions that best served both goals.
