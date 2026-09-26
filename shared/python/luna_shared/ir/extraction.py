"""HTML content extraction into structured document fields."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from luna_shared.utils.url import extract_domain, is_valid_url, normalize_url

_NON_CONTENT = ["script", "style", "noscript", "iframe", "svg", "canvas", "header",
                "footer", "nav", "aside", "form"]


@dataclass
class ExtractedPage:
    url: str
    canonical_url: str
    title: str | None
    meta_description: str | None
    headings: dict[str, list[str]]
    body_text: str
    outlinks: list[str] = field(default_factory=list)
    images: list[str] = field(default_factory=list)
    language: str = "en"
    content_hash: str = ""

    def compute_hash(self) -> str:
        h = hashlib.sha256()
        h.update((self.title or "").encode())
        h.update(b"\x00")
        h.update(self.body_text.encode())
        self.content_hash = h.hexdigest()
        return self.content_hash


def _clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def extract_page(html: str, url: str) -> ExtractedPage:
    """Parse HTML into structured fields with cleaned text and links."""
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup(_NON_CONTENT):
        tag.decompose()

    title = None
    if soup.title and soup.title.string:
        title = _clean_text(soup.title.string)

    meta_description = None
    meta = soup.find("meta", attrs={"name": "description"}) or soup.find(
        "meta", attrs={"property": "og:description"}
    )
    if meta and meta.get("content"):
        meta_description = _clean_text(meta["content"])

    canonical = url
    link_canonical = soup.find("link", attrs={"rel": "canonical"})
    if link_canonical and link_canonical.get("href"):
        canonical = urljoin(url, link_canonical["href"])

    lang = "en"
    if soup.html and soup.html.get("lang"):
        lang = soup.html["lang"].split("-")[0].lower()[:10] or "en"

    headings: dict[str, list[str]] = {}
    for level in ("h1", "h2", "h3", "h4", "h5", "h6"):
        texts = [_clean_text(h.get_text()) for h in soup.find_all(level)]
        texts = [t for t in texts if t]
        if texts:
            headings[level] = texts

    body_text = _clean_text(soup.get_text(separator=" "))

    outlinks: list[str] = []
    seen_links: set[str] = set()
    for anchor in soup.find_all("a", href=True):
        try:
            absolute = urljoin(url, anchor["href"])
        except Exception:
            continue
        if not is_valid_url(absolute):
            continue
        norm = normalize_url(absolute)
        if norm not in seen_links:
            seen_links.add(norm)
            outlinks.append(norm)

    images: list[str] = []
    seen_imgs: set[str] = set()
    for img in soup.find_all("img", src=True):
        try:
            img_url = urljoin(url, img["src"])
            norm_img = normalize_url(img_url)
            if norm_img not in seen_imgs:
                seen_imgs.add(norm_img)
                images.append(norm_img)
        except Exception:
            continue

    page = ExtractedPage(
        url=normalize_url(url),
        canonical_url=normalize_url(canonical),
        title=title,
        meta_description=meta_description,
        headings=headings,
        body_text=body_text,
        outlinks=outlinks,
        images=images,
        language=lang,
    )
    page.compute_hash()
    return page


def heading_text(headings: dict[str, list[str]]) -> str:
    """Flatten a headings dict into a single string for indexing."""
    parts: list[str] = []
    for values in headings.values():
        parts.extend(values)
    return " ".join(parts)


def domain_of(url: str) -> str:
    return extract_domain(url)


__all__ = ["ExtractedPage", "domain_of", "extract_page", "heading_text"]
