# Operations

## Seeding demo data

```bash
uv run python scripts/seed_demo_data.py
```

Deterministic and idempotent. Creates three users, a completed demo crawl job,
eight interlinked documents, the full inverted index, PageRank scores, and
sample query/click logs. Re-running updates in place without duplicating.

Demo accounts:

| Email | Password | Role |
|---|---|---|
| admin@nexussearch.dev | admin123 | admin |
| operator@nexussearch.dev | operator123 | operator |
| viewer@nexussearch.dev | viewer123 | viewer |

## Running a crawl

Create a job (admin/operator), then run it:

```bash
# via the admin API (through the gateway)
curl -X POST http://localhost:8000/api/v1/admin/crawl/jobs \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"name":"my-crawl","seed_urls":["https://example.com"],"allowed_domains":["example.com"],"max_depth":2,"max_pages":100}'

# trigger execution (crawler service)
curl -X POST http://localhost:8002/api/v1/crawl/run \
  -H 'Content-Type: application/json' -d '{"job_id":"<id>","max_pages":100}'
```

The crawler respects `robots.txt`, per-domain delay and concurrency, and only
crawls allowed domains. Discovered links are enqueued up to `max_depth`.

## Recomputing PageRank

PageRank is computed over the whole document link graph and persisted on each
document:

```bash
uv run python scripts/compute_pagerank.py
# or via the ranker service:
curl -X POST http://localhost:8004/api/v1/rank/pagerank
```

Run it after a crawl completes (or on a schedule) to refresh authority scores.

## Tuning ranking

Edit `config/ranking.yaml`:

- `bm25.k1`, `bm25.b` — term-frequency saturation and length normalization.
- `field_weights` — relative importance of title / heading / body / etc.
- `scoring.bm25_weight`, `pagerank_weight`, `freshness_weight` — final blend.

Some values are also exposed as runtime-tunable settings through
`PUT /api/v1/admin/settings/{key}` (allowlisted keys only).

## Monitoring

- Each service emits structured JSON logs with a `request_id` for correlation.
- `GET /health/ready` on any service reports dependency status.
- `GET /api/v1/admin/analytics/queries` shows query volume, top and zero-result
  queries, click-through rate, and latency percentiles.

## Benchmarks

`scripts/benchmark_search.py` is a starting point for load testing. Throughput
and latency targets in the plan are **unmeasured design goals** until run on
representative infrastructure.
