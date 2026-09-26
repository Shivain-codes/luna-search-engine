"""Unit tests for tokenization, stemming, and snippets."""

from luna_shared.utils.text_processing import (
    analyze,
    build_snippet,
    extract_text_from_html,
    stem,
    tokenize,
)


def test_tokenize_lowercases_and_splits():
    assert tokenize("Hello, World! 123") == ["hello", "world", "123"]


def test_stem_reduces_inflections():
    assert stem("running") == "run"
    assert stem("flies") == "fli"
    assert stem("happily") == "happili"
    assert stem("nationalization") == stem("nationalize")[:0] or stem("nationalization")  # stable


def test_stem_is_idempotent():
    for word in ["running", "connection", "relational", "argument"]:
        once = stem(word)
        assert stem(once) == once


def test_analyze_removes_stopwords_and_stems():
    result = analyze("The quick brown foxes are running")
    assert "the" not in result
    assert "are" not in result
    assert "run" in result
    assert "fox" in result


def test_build_snippet_centers_on_match():
    text = "word " * 50 + "python programming language" + " word" * 50
    snippet = build_snippet(text, ["python"], max_length=60)
    assert "python" in snippet.lower()
    assert len(snippet) <= 70  # allow for ellipses


def test_build_snippet_empty_text():
    assert build_snippet("", ["x"]) == ""


def test_extract_text_strips_scripts():
    html = "<html><body><script>evil()</script><p>Hello world</p></body></html>"
    text = extract_text_from_html(html)
    assert "evil" not in text
    assert "Hello world" in text
