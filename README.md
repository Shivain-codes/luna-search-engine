# Luna Search Engine

#### Video Demo: <URL HERE>

#### Description

Luna is a working search engine built from scratch for my CS50 final project. Instead of calling an existing search API, I implemented the core machinery that makes a search engine work — a web crawler, a custom inverted index, the BM25 relevance ranking function, and the PageRank link-analysis algorithm — and wrapped them in a microservice backend with a React/TypeScript frontend. The goal was to understand and build the computer science behind search, not just glue together someone else's library.

At a high level, Luna does four things. It **crawls** web pages politely, extracting clean text, titles, headings, metadata, and links. It **indexes** those pages into a positional inverted index and maintains global term statistics. It **ranks** matching documents using BM25 combined with PageRank and freshness. And it **serves** search and autocomplete through an API gateway, tracking query and click analytics along the way.

#### The algorithms

**Inverted index.** The heart of any search engine is the inverted index, which maps each *term* to the list of documents that contain it. For every `(term, document, field)` combination, Luna stores the term frequency and the exact token *positions* within that field. Positions are what make phrase and proximity matching possible. I index fields separately — title, headings, body, metadata, and URL — so the ranker can weight a title match more heavily than a body match. Global term statistics (document frequency and inverse document frequency) are maintained incrementally so scoring never has to scan the whole corpus at query time.

**BM25.** BM25 is the standard bag-of-words relevance function used by real search engines. For each query term appearing in a document field, the contribution is `IDF · tf·(k1+1) / (tf + k1·(1 − b + b·|field|/avgFieldLen))`, with `k1 = 1.5` and `b = 0.75`. The IDF term rewards rare words, the term-frequency component saturates so repeating a word many times has diminishing returns, and the length-normalization factor prevents long documents from dominating. I sum this across all query terms and fields, each multiplied by its field weight. To be confident my implementation was correct, I wrote a property-based test (using Hypothesis) that generates random corpora and asserts my score equals a direct evaluation of the formula — this caught two normalization bugs early.

**PageRank.** PageRank measures how authoritative a page is based on the web's link graph: a page linked to by many important pages is itself important. I implemented it with power iteration, a damping factor of 0.85, redistribution of "dangling node" mass, and a convergence tolerance. The result is normalized so all scores sum to 1. Property tests verify the invariants (scores are non-negative, sum to 1, and the algorithm terminates) for arbitrary graphs, including tricky ones with dangling nodes. The final ranking blends BM25 relevance, PageRank authority, and freshness with configurable weights.

**Query processing.** Queries are normalized and parsed into required terms, excluded terms (`-word`), exact phrases (`"..."`), and field operators (`site:`, `intitle:`, `inurl:`). Terms are stemmed with a Porter stemmer I wrote from scratch, so `running`, `runs`, and `run` all match.

#### Architecture

Luna is organized as six small backend services plus a frontend, mirroring how real search systems separate concerns. The **API gateway** is the only public entry point; it handles routing, rate limiting, and CORS. The **search API** owns the query pipeline. The **crawler** and **indexer** are asynchronous workers connected by a message queue. The **ranker** is pure computation. The **admin API** owns authentication, role-based access control, and management operations.

A key design decision was making the data layer *portable*: the same models run on PostgreSQL in production and on SQLite for local development, and the cache and message broker each have an in-memory backend. This means the entire system runs and is fully testable with no external infrastructure, while the production path (PostgreSQL, Redis, RabbitMQ via Docker Compose) stays intact.

#### Files

`shared/python/nexus_shared/` holds the shared library: `ir/` contains the algorithms (bm25, pagerank, query parser, extraction, indexing), `models/` the database schema, `repositories/` the data-access layer, and `security/` the auth, JWT, and RBAC code. `services/` contains the six FastAPI services. `frontend/` is the React app. `scripts/` has helpers to seed demo data, run everything locally, crawl, and verify the pipeline. `tests/` holds unit, property-based, and integration tests.

#### Running it

```bash
uv sync --group dev
uv run python scripts/bootstrap.py
uv run python scripts/seed_demo_data.py
uv run python scripts/run_local.py
cd frontend && npm install && npm run dev
```

Then open http://localhost:3000. The admin dashboard login is `admin@nexussearch.dev` / `admin123`. See `docs/` for architecture, API, deployment, and operations guides.
