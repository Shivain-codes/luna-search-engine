"""URL handling utilities for normalization, canonicalization, and validation."""
import hashlib
import re
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse

# Common tracking parameters to strip
TRACKING_PARAMS: set[str] = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "fbclid", "gclid", "msclkid", "twclid", "igshid",
    "ref", "source", "medium", "campaign",
    "_ga", "_gl", "_hsenc", "_hsmi",
    "mc_cid", "mc_eid",
    "amp",
}

# File extensions to skip
SKIP_EXTENSIONS: set[str] = {
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    ".zip", ".rar", ".tar", ".gz", ".7z", ".bz2",
    ".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".ico", ".bmp", ".tiff",
    ".mp4", ".mp3", ".avi", ".mov", ".wmv", ".flv", ".mkv",
    ".css", ".js", ".woff", ".woff2", ".ttf", ".eot",
    ".exe", ".dmg", ".pkg", ".deb", ".rpm", ".apk",
}


def normalize_url(url: str) -> str:
    """Normalize URL by lowercasing host, removing default ports, etc."""
    try:
        parsed = urlparse(url.strip())
        if not parsed.scheme or not parsed.netloc:
            return url

        # Lowercase scheme and host
        scheme = parsed.scheme.lower()
        netloc = parsed.netloc.lower()

        # Remove default ports
        if (scheme == "http" and netloc.endswith(":80")) or \
           (scheme == "https" and netloc.endswith(":443")):
            netloc = netloc.rsplit(":", 1)[0]

        # Remove www. prefix for canonicalization (optional)
        # netloc = netloc.removeprefix("www.")

        # Remove fragment
        fragment = ""

        # Sort query parameters for consistency
        query_params = parse_qsl(parsed.query, keep_blank_values=True)
        # Filter out tracking parameters
        query_params = [(k, v) for k, v in query_params if k not in TRACKING_PARAMS]
        query_params.sort()
        query = urlencode(query_params)

        return urlunparse((scheme, netloc, parsed.path.rstrip("/") or "/", "", query, fragment))
    except Exception:
        return url


def canonicalize_url(url: str, base_url: str | None = None) -> str:
    """Resolve relative URLs and normalize."""
    if base_url:
        url = urljoin(base_url, url)
    return normalize_url(url)


def is_valid_url(url: str) -> bool:
    """Check if URL is valid and uses HTTP/HTTPS."""
    try:
        parsed = urlparse(url)
        return parsed.scheme in ("http", "https") and bool(parsed.netloc)
    except Exception:
        return False


def should_crawl_url(url: str, allowed_domains: list[str] | None = None,
                     blocked_domains: list[str] | None = None) -> bool:
    """Check if URL should be crawled based on rules."""
    if not is_valid_url(url):
        return False

    parsed = urlparse(url)

    # Skip file extensions
    path_lower = parsed.path.lower()
    if any(path_lower.endswith(ext) for ext in SKIP_EXTENSIONS):
        return False

    # Check allowed domains
    if allowed_domains:
        if not any(parsed.netloc == d or parsed.netloc.endswith("." + d) for d in allowed_domains):
            return False

    # Check blocked domains
    if blocked_domains:
        if any(parsed.netloc == d or parsed.netloc.endswith("." + d) for d in blocked_domains):
            return False

    return True


def extract_domain(url: str) -> str:
    """Extract domain from URL."""
    try:
        return urlparse(url).netloc.lower()
    except Exception:
        return ""


def url_hash(url: str) -> str:
    """Generate SHA256 hash of normalized URL."""
    normalized = normalize_url(url)
    return hashlib.sha256(normalized.encode()).hexdigest()


def extract_links(html: str, base_url: str) -> list[str]:
    """Extract all links from HTML."""
    # Simple regex for href attributes
    pattern = r'href=["\']([^"\']+)["\']'
    matches = re.findall(pattern, html, re.IGNORECASE)
    links = []
    for match in matches:
        try:
            absolute = urljoin(base_url, match)
            if is_valid_url(absolute):
                links.append(normalize_url(absolute))
        except Exception:
            continue
    return list(set(links))


def get_robots_txt_url(url: str) -> str:
    """Get robots.txt URL for a given URL."""
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}/robots.txt"


def is_same_domain(url1: str, url2: str) -> bool:
    """Check if two URLs are on the same domain."""
    return extract_domain(url1) == extract_domain(url2)


def is_subdomain(url: str, domain: str) -> bool:
    """Check if URL is on a subdomain of domain."""
    url_domain = extract_domain(url)
    return url_domain == domain or url_domain.endswith("." + domain)
