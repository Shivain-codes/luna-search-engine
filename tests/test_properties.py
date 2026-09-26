"""Property-based tests for the IR core (Feature: complete-search-engine-project)."""

import math

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from luna_shared.ir.bm25 import BM25Config, BM25Scorer, idf
from luna_shared.ir.pagerank import compute_pagerank
from luna_shared.ir.query import parse_query

pytestmark = pytest.mark.property


# Property 8: BM25 agrees with the configured reference formula.
@settings(max_examples=150)
@given(
    num_docs=st.integers(min_value=1, max_value=10_000),
    df=st.integers(min_value=1, max_value=1000),
    tf=st.integers(min_value=1, max_value=100),
    field_length=st.integers(min_value=1, max_value=5000),
    k1=st.floats(min_value=0.5, max_value=3.0),
    b=st.floats(min_value=0.0, max_value=1.0),
)
def test_property_bm25_matches_reference(num_docs, df, tf, field_length, k1, b):
    df = min(df, num_docs)
    cfg = BM25Config(k1=k1, b=b, field_weights={"body": 1.0}, avg_field_length={"body": 300.0})
    scorer = BM25Scorer(cfg, num_docs=num_docs)
    score = scorer.term_score(
        doc_frequency=df, term_frequency=tf, field="body", field_length=field_length
    )
    expected_idf = max(0.0, math.log((num_docs - df + 0.5) / (df + 0.5) + 1))
    norm = 1 - b + b * (field_length / 300.0)
    expected = expected_idf * (tf * (k1 + 1)) / (tf + k1 * norm)
    assert score == pytest.approx(expected, rel=1e-9, abs=1e-9)


# Property 9: PageRank invariants for any finite graph.
@settings(max_examples=100)
@given(
    n=st.integers(min_value=1, max_value=15),
    edge_seeds=st.lists(
        st.tuples(st.integers(0, 14), st.integers(0, 14)), max_size=40
    ),
)
def test_property_pagerank_invariants(n, edge_seeds):
    nodes = [str(i) for i in range(n)]
    edges = [(str(a % n), str(b % n)) for a, b in edge_seeds]
    scores = compute_pagerank(nodes, edges, max_iterations=100)
    assert set(scores.keys()) == set(nodes)
    assert all(v >= 0 for v in scores.values())
    assert sum(scores.values()) == pytest.approx(1.0, abs=1e-6)


# idf is always non-negative.
@settings(max_examples=100)
@given(
    num_docs=st.integers(min_value=1, max_value=100_000),
    df=st.integers(min_value=0, max_value=100_000),
)
def test_property_idf_non_negative(num_docs, df):
    assert idf(num_docs, min(df, num_docs)) >= 0.0


# Property 3 (partial): query parsing never loses excluded markers.
@settings(max_examples=100)
@given(
    terms=st.lists(
        st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=1, max_size=8),
        min_size=1,
        max_size=5,
    )
)
def test_property_excluded_terms_never_required(terms):
    query = " ".join(f"-{t}" for t in terms)
    pq = parse_query(query)
    # Every excluded token must appear in excluded, none in required.
    for t in terms:
        assert t in pq.excluded
    assert pq.required == []
