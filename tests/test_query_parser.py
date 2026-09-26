"""Unit tests for the query parser."""

from luna_shared.ir.query import normalize_query, parse_query


def test_normalize_collapses_whitespace_and_lowercases():
    assert normalize_query("  Hello   WORLD  ") == "hello world"


def test_parse_required_and_excluded():
    pq = parse_query("python -java")
    assert "python" in pq.required
    assert "java" in pq.excluded


def test_parse_phrase():
    pq = parse_query('"web crawler" python')
    assert "web crawler" in pq.phrases
    assert "python" in pq.required


def test_parse_field_operators():
    pq = parse_query("guide site:github.com intitle:python inurl:docs")
    assert pq.filters["site"] == "github.com"
    assert pq.filters["intitle"] == "python"
    assert pq.filters["inurl"] == "docs"


def test_terms_are_stemmed():
    pq = parse_query("running programs")
    assert "run" in pq.terms
    assert "program" in pq.terms


def test_empty_query_is_empty():
    assert parse_query("").is_empty
    assert parse_query("   ").is_empty
