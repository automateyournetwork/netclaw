"""URL fetching + depth-1 same-domain link discovery for rag-mcp (FR-004).

Two-phase protocol: preview (title + in-scope linked pages + scope token,
no ingestion) then ingest (single page, or linked pages with a valid echoed
scope token). The token makes the crawl-confirmation gate structural.
"""

import hashlib
import hmac
import os
import secrets
from typing import Dict, List, Tuple
from urllib.parse import urldefrag, urljoin, urlparse

from ingestion.local_https import fetch_local_https

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


def fetch(url: str, timeout: float = 30.0, max_bytes: int = 100 * 1024 * 1024,
          verify_ssl: bool = True) -> Tuple[bytes, str]:
    """Fetch under a decoded-byte cap, including chunked/compressed responses."""
    import httpx

    if max_bytes <= 0:
        raise FetchError("Document byte limit must be positive")
    try:
        local = fetch_local_https(url, timeout, max_bytes, verify_ssl)
        if local is not None:
            return local
        options = {"verify": False} if not verify_ssl else {}
        with httpx.stream("GET", url, timeout=timeout, follow_redirects=verify_ssl, **options) as resp:
            resp.raise_for_status()
            content_type = resp.headers.get("content-type", "").split(";")[0].strip().lower()
            chunks, size = [], 0
            for chunk in resp.iter_bytes(chunk_size=min(65536, max_bytes + 1)):
                size += len(chunk)
                if size > max_bytes:
                    raise FetchError(f"Document exceeds the {max_bytes}-byte download limit")
                chunks.append(chunk)
            return b"".join(chunks), content_type
    except FetchError:
        raise
    except Exception as exc:
        raise FetchError(f"Could not fetch {url}: {exc}")


def discover_links(html: str, base_url: str, max_pages: int) -> Dict:
    """Same-domain depth-1 links from a page. Returns
    {linked_pages: [{url, title?}], truncated: bool}."""
    from bs4 import BeautifulSoup

    return _discover_links(BeautifulSoup(html, "html.parser"), base_url, max_pages)


def _discover_links(soup, base_url: str, max_pages: int) -> Dict:
    base_host = urlparse(base_url).netloc
    base_clean = urldefrag(base_url)[0]

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


def preview_html(html: str, base_url: str, max_pages: int) -> Dict:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    title = soup.title.get_text(" ", strip=True) if soup.title else base_url
    links = _discover_links(soup, base_url, max_pages)
    scripts = len(soup.find_all("script"))
    for tag in soup(["head", "script", "style", "noscript", "svg"]):
        tag.decompose()
    text_chars = len(soup.get_text(" ", strip=True))
    thin = text_chars < 80
    spa_shell = thin and scripts > 0 and len(links["linked_pages"]) <= 1
    warning = None
    if spa_shell:
        warning = "Likely JavaScript application shell. Request the static documentation or OpenAPI JSON."
    elif thin:
        warning = "Very little visible text. Check that this page contains the intended document."
    return {**links, "title": title, "text_chars": text_chars, "thin": thin,
            "spa_shell": spa_shell, "warning": warning}


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
    if content_type == "application/json" or content_type.endswith("+json"):
        ext = ".json"
    elif content_type == "text/plain" and stem.lower().endswith(".json"):
        ext = ".json"
    if ext and not stem.lower().endswith(ext):
        stem += ext
    if "." not in stem:
        stem += ".html"
    return f"url_{digest}_{stem}"
