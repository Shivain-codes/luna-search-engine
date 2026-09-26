"""Simple search benchmark harness.

Fires concurrent search requests at a running gateway and reports throughput
and latency percentiles. This measures whatever environment you run it against;
the plan's targets are goals, not guarantees.

Usage:
    uv run python scripts/benchmark_search.py --url http://localhost:8000 --n 500 --concurrency 20
"""

from __future__ import annotations

import argparse
import asyncio
import time

import httpx

QUERIES = [
    # Common
    "python programming",
    "machine learning",
    "how search engines work",
    "data science",
    "web development",
    # Rare/Technical
    "levenshtein distance implementation",
    "pagerank convergence rate",
    "bm25 ranking formula",
    "inverted index positional mapping",
    # Boolean/Complex
    "python AND machine learning",
    "search -google",
    "\"distributed systems\" site:edu",
    "intitle:search engine",
    "inurl:api",
]


async def worker(client: httpx.AsyncClient, url: str, n: int, latencies: list[float]) -> None:
    for i in range(n):
        q = QUERIES[i % len(QUERIES)]
        start = time.perf_counter()
        try:
            resp = await client.get(f"{url}/api/v1/search", params={"q": q, "per_page": 10})
            resp.raise_for_status()
        except httpx.HTTPError:
            continue
        latencies.append((time.perf_counter() - start) * 1000)


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    k = max(0, min(len(ordered) - 1, round(pct / 100 * (len(ordered) - 1))))
    return ordered[k]


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8000")
    parser.add_argument("--n", type=int, default=200, help="requests per worker")
    parser.add_argument("--concurrency", type=int, default=10)
    args = parser.parse_args()

    latencies: list[float] = []
    start = time.perf_counter()
    async with httpx.AsyncClient(timeout=30.0) as client:
        await asyncio.gather(
            *[worker(client, args.url, args.n, latencies) for _ in range(args.concurrency)]
        )
    elapsed = time.perf_counter() - start
    total = len(latencies)

    print(f"environment:  {args.url}")
    print(f"requests:     {total} ({args.concurrency} workers x {args.n})")
    print(f"wall time:    {elapsed:.2f}s")
    print(f"throughput:   {total / elapsed:.1f} req/s")
    print(f"latency p50:  {percentile(latencies, 50):.1f} ms")
    print(f"latency p95:  {percentile(latencies, 95):.1f} ms")
    print(f"latency p99:  {percentile(latencies, 99):.1f} ms")
    print("\nNote: results reflect THIS environment. Plan targets remain goals.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
