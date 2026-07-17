"""URL fetching + depth-1 same-domain link discovery for rag-mcp (FR-004).

Two-phase protocol: preview (title + in-scope linked pages + scope token,
no ingestion) then ingest (single page, or linked pages with a valid echoed
scope token). The token makes the crawl-confirmation gate structural.
"""

import hashlib
import hmac
import os
import secrets
from typing import Dict, List, Optional, Tuple
from urllib.parse import urldefrag, urljoin, urlparse

# Per-process signing key: a scope token is only valid within the server
# process that issued the preview (a restart forces a fresh preview).
_SCOPE_KEY = os.environ.get("RAG_SCOPE_KEY") or secrets.token_hex(16)


class FetchError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


def scope_token(url: str, linked_urls: List[str]) -> str:
    payload = url + "|" + "|".join(sorted(linked_urls))
    return hmac.new(_SCOPE_KEY.encode(), payload.encode(), hashlib.sha256).hexdigest()[:32]


def verify_scope_token(token: str, url: str, linked_urls: List[str]) -> bool:
    return hmac.compare_digest(token or "", scope_token(url, linked_urls))


def fetch(url: str, timeout: float = 30.0) -> Tuple[bytes, str]:
    """Fetch a URL. Returns (content_bytes, content_type). Errors verbatim."""
    import httpx

    try:
        resp = httpx.get(url, timeout=timeout, follow_redirects=True)
        resp.raise_for_status()
    except Exception as exc:
        raise FetchError(f"Could not fetch {url}: {exc}")
    content_type = resp.headers.get("content-type", "").split(";")[0].strip().lower()
    return resp.content, content_type


def discover_links(html: str, base_url: str, max_pages: int) -> Dict:
    """Same-domain depth-1 links from a page. Returns
    {linked_pages: [{url, title?}], truncated: bool}."""
    from bs4 import BeautifulSoup

    base_host = urlparse(base_url).netloc
    base_clean = urldefrag(base_url)[0]
    soup = BeautifulSoup(html, "html.parser")

    seen, linked = set(), []
    truncated = False
    for a in soup.find_all("a", href=True):
        href = urldefrag(urljoin(base_url, a["href"]))[0]
        parsed = urlparse(href)
        if parsed.scheme not in ("http", "https"):
            continue
        if parsed.netloc != base_host:  # same-domain only
            continue
        if href == base_clean or href in seen:
            continue
        seen.add(href)
        if len(linked) >= max_pages:
            truncated = True
            break
        text = a.get_text(" ", strip=True)
        linked.append({"url": href, "title": text[:120] if text else None})
    return {"linked_pages": linked, "truncated": truncated}


def page_title(html: str, fallback: str) -> str:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    if soup.title and soup.title.string:
        return soup.title.string.strip()
    return fallback


def filename_for_url(url: str, content_type: str) -> str:
    """Stable intake filename for a fetched URL."""
    parsed = urlparse(url)
    stem = (parsed.path.rstrip("/").rsplit("/", 1)[-1] or parsed.netloc).split("?")[0]
    digest = hashlib.sha256(url.encode()).hexdigest()[:8]
    ext_map = {
        "text/html": ".html",
        "application/pdf": ".pdf",
        "text/plain": ".txt",
        "text/markdown": ".md",
    }
    ext = ext_map.get(content_type, "")
    if ext and not stem.lower().endswith(ext):
        stem += ext
    if "." not in stem:
        stem += ".html"
    return f"url_{digest}_{stem}"
