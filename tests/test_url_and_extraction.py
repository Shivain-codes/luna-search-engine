"""Unit tests for URL normalization and HTML extraction."""

from luna_shared.ir.extraction import extract_page
from luna_shared.utils.url import (
    extract_domain,
    is_valid_url,
    normalize_url,
    should_crawl_url,
)


def test_normalize_strips_tracking_params():
    url = "https://Example.com/Path/?utm_source=x&b=2&a=1"
    normalized = normalize_url(url)
    assert "utm_source" not in normalized
    assert normalized.startswith("https://example.com")


def test_normalize_is_idempotent():
    url = "https://example.com/a?b=2&a=1"
    assert normalize_url(normalize_url(url)) == normalize_url(url)


def test_is_valid_url():
    assert is_valid_url("https://example.com")
    assert not is_valid_url("ftp://example.com")
    assert not is_valid_url("not a url")


def test_should_crawl_respects_domains():
    assert should_crawl_url("https://a.com/x", allowed_domains=["a.com"])
    assert not should_crawl_url("https://b.com/x", allowed_domains=["a.com"])
    assert not should_crawl_url("https://a.com/x", blocked_domains=["a.com"])


def test_should_crawl_skips_binary_extensions():
    assert not should_crawl_url("https://a.com/file.pdf")
    assert should_crawl_url("https://a.com/page.html")


def test_extract_domain():
    assert extract_domain("https://sub.example.com/path") == "sub.example.com"


def test_extract_page_fields():
    html = """
    <html lang="en"><head><title>My Title</title>
    <meta name="description" content="A description">
    <link rel="canonical" href="https://x.com/canonical"></head>
    <body><h1>Heading</h1><script>bad()</script>
    <p>Body content here</p><a href="/next">link</a></body></html>
    """
    page = extract_page(html, "https://x.com/page?utm_source=t")
    assert page.title == "My Title"
    assert page.meta_description == "A description"
    assert page.canonical_url == "https://x.com/canonical"
    assert page.language == "en"
    assert "h1" in page.headings
    assert "bad" not in page.body_text
    assert "Body content here" in page.body_text
    assert len(page.outlinks) == 1
    assert len(page.content_hash) == 64


def test_extract_page_deterministic_hash():
    html = "<html><head><title>T</title></head><body><p>same</p></body></html>"
    a = extract_page(html, "https://x.com/a")
    b = extract_page(html, "https://x.com/a")
    assert a.content_hash == b.content_hash
