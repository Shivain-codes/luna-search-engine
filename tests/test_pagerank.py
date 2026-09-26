"""Unit tests for PageRank."""

from luna_shared.ir.pagerank import compute_pagerank


def test_empty_graph():
    assert compute_pagerank([], []) == {}


def test_scores_sum_to_one_and_non_negative():
    nodes = ["a", "b", "c", "d"]
    edges = [("a", "b"), ("b", "c"), ("c", "a"), ("d", "c")]
    scores = compute_pagerank(nodes, edges)
    assert abs(sum(scores.values()) - 1.0) < 1e-6
    assert all(v >= 0 for v in scores.values())


def test_authority_ranks_higher():
    # c is linked by a, b, and d -> should have highest score.
    nodes = ["a", "b", "c", "d"]
    edges = [("a", "c"), ("b", "c"), ("d", "c"), ("a", "b")]
    scores = compute_pagerank(nodes, edges)
    assert scores["c"] == max(scores.values())


def test_dangling_nodes_handled():
    # 'b' has no outlinks (dangling).
    nodes = ["a", "b"]
    edges = [("a", "b")]
    scores = compute_pagerank(nodes, edges)
    assert abs(sum(scores.values()) - 1.0) < 1e-6


def test_converges_within_iterations():
    nodes = [str(i) for i in range(20)]
    edges = [(str(i), str((i + 1) % 20)) for i in range(20)]
    scores = compute_pagerank(nodes, edges, max_iterations=100)
    # Ring graph -> roughly uniform.
    values = list(scores.values())
    assert max(values) - min(values) < 0.01
