"""PageRank via power iteration (pure Python, no numpy dependency)."""

from __future__ import annotations

from collections.abc import Iterable


def compute_pagerank(
    nodes: Iterable[str],
    edges: Iterable[tuple[str, str]],
    *,
    damping: float = 0.85,
    max_iterations: int = 100,
    tolerance: float = 1e-6,
    dangling: str = "uniform",
) -> dict[str, float]:
    """Compute PageRank scores.

    Args:
        nodes: all node identifiers.
        edges: directed ``(source, target)`` links.
        damping: probability of following a link.
        max_iterations: iteration cap.
        tolerance: L1 convergence threshold.
        dangling: handling for nodes with no out-links ("uniform" spreads
            their mass across all nodes).

    Returns:
        Mapping of node -> normalized score (scores sum to 1.0).
    """
    node_list = list(dict.fromkeys(nodes))
    n = len(node_list)
    if n == 0:
        return {}

    index = {node: i for i, node in enumerate(node_list)}
    out_links: list[list[int]] = [[] for _ in range(n)]
    for src, dst in edges:
        if src in index and dst in index and src != dst:
            out_links[index[src]].append(index[dst])

    rank = [1.0 / n] * n
    base = (1.0 - damping) / n

    for _ in range(max_iterations):
        new_rank = [base] * n
        dangling_mass = 0.0
        for i in range(n):
            targets = out_links[i]
            if not targets:
                dangling_mass += rank[i]
                continue
            share = damping * rank[i] / len(targets)
            for j in targets:
                new_rank[j] += share
        if dangling == "uniform" and dangling_mass > 0:
            spread = damping * dangling_mass / n
            new_rank = [r + spread for r in new_rank]

        delta = sum(abs(new_rank[i] - rank[i]) for i in range(n))
        rank = new_rank
        if delta < tolerance:
            break

    total = sum(rank) or 1.0
    return {node_list[i]: rank[i] / total for i in range(n)}


__all__ = ["compute_pagerank"]
