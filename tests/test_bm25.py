"""Unit tests for BM25 scoring against the reference formula."""

import math

from luna_shared.ir.bm25 import BM25Config, BM25Scorer, idf


def test_idf_non_negative_and_monotonic():
    # Rarer terms (lower df) have higher idf.
    assert idf(100, 1) > idf(100, 50)
    assert idf(100, 100) >= 0.0


def test_term_score_matches_reference_formula():
    cfg = BM25Config(k1=1.5, b=0.75)
    scorer = BM25Scorer(cfg, num_docs=10)
    score = scorer.term_score(doc_frequency=3, term_frequency=2, field="body", field_length=500)

    k1, b, avgdl, n, df, tf = 1.5, 0.75, 500.0, 10, 3, 2
    expected_idf = max(0.0, math.log((n - df + 0.5) / (df + 0.5) + 1))
    norm = 1 - b + b * (500 / avgdl)
    expected = expected_idf * (tf * (k1 + 1)) / (tf + k1 * norm)
    assert abs(score - expected) < 1e-9


def test_field_weights_applied():
    cfg = BM25Config()
    scorer = BM25Scorer(cfg, num_docs=10)
    title = scorer.term_score(doc_frequency=3, term_frequency=2, field="title", field_length=8)
    body = scorer.term_score(doc_frequency=3, term_frequency=2, field="body", field_length=8)
    # Title weight (3.0) > body weight (1.0)
    assert title > body


def test_score_document_sums_over_terms_and_fields():
    cfg = BM25Config()
    scorer = BM25Scorer(cfg, num_docs=5)
    score = scorer.score_document(
        ["python", "guide"],
        doc_frequencies={"python": 2, "guide": 1},
        postings={"python": {"title": 1, "body": 3}, "guide": {"body": 1}},
        field_lengths={"title": 8, "body": 200},
    )
    assert score > 0


def test_missing_term_contributes_zero():
    cfg = BM25Config()
    scorer = BM25Scorer(cfg, num_docs=5)
    score = scorer.score_document(
        ["absent"],
        doc_frequencies={},
        postings={},
        field_lengths={},
    )
    assert score == 0.0
