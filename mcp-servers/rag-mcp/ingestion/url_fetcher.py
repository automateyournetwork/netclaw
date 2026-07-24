"""URL fetching + depth-1 same-domain link discovery for rag-mcp (FR-004).

Two-phase protocol: preview (title + in-scope linked pages + scope token,
no ingestion) then ingest (single page, or linked pages with a valid echoed
scope token). The token makes the crawl-confirmation gate structural.
"""

import hashlib
import hmac
import os
import re
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


def is_private_or_local_host(url: str) -> bool:
    """True for localhost / RFC1918 / link-local hosts (typical home-lab gear)."""
    import ipaddress

    host = (urlparse(url).hostname or "").strip().lower()
    if not host:
        return False
    if host in ("localhost", "localhost.localdomain") or host.endswith(".local"):
        return True
    try:
        ip = ipaddress.ip_address(host)
        return bool(
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
        )
    except ValueError:
        # Hostname — treat common home suffixes as local
        return host.endswith((".lan", ".home", ".internal", ".home.arpa"))


def resolve_verify_ssl(url: str, verify_ssl: Optional[bool] = None) -> bool:
    """Decide TLS certificate verification.

    Priority:
      1. Explicit verify_ssl argument (tool / HUD)
      2. RAG_URL_VERIFY_SSL env: true|false|auto (default auto)
      3. auto → False for private/local hosts, True otherwise
    """
    if verify_ssl is not None:
        return bool(verify_ssl)
    mode = (os.environ.get("RAG_URL_VERIFY_SSL") or "auto").strip().lower()
    if mode in ("0", "false", "no", "off", "insecure"):
        return False
    if mode in ("1", "true", "yes", "on", "force"):
        return True
    # auto
    return not is_private_or_local_host(url)


def _httpx_http2_available() -> bool:
    """True when the optional ``h2`` package is importable (httpx HTTP/2 support)."""
    try:
        import h2  # noqa: F401

        return True
    except ImportError:
        return False


def _curl_available() -> bool:
    import shutil

    return bool(shutil.which("curl"))


def _fetch_with_curl(
    url: str,
    timeout: float,
    verify: bool,
) -> Tuple[bytes, str]:
    """Fetch via system curl (HTTP/2 ALPN). UniFi OS often hangs on httpx HTTP/2.

    Returns (body_bytes, content_type). Raises FetchError on failure.
    """
    import re
    import shutil
    import subprocess
    import tempfile

    curl = shutil.which("curl")
    if not curl:
        raise FetchError("curl not found on PATH")

    max_time = max(1, int(timeout + 0.999))
    with tempfile.TemporaryDirectory(prefix="netclaw-fetch-") as td:
        body_path = f"{td}/body"
        hdr_path = f"{td}/hdr"
        cmd = [
            curl,
            "-sS",
            "-L",
            "--http2",
            "--max-time",
            str(max_time),
            "--connect-timeout",
            str(min(10, max_time)),
            "-D",
            hdr_path,
            "-o",
            body_path,
            "-w",
            "%{http_code}",
            "-A",
            "NetClaw-rag-url/1.0 (+curl; local Knowledge ingest)",
            "-H",
            "Accept: text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
        ]
        if not verify:
            cmd.append("-k")
        # Avoid leaking LAN fetches through an ambient HTTP(S)_PROXY.
        if is_private_or_local_host(url):
            cmd.extend(["--noproxy", "*"])
        cmd.append(url)

        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=max_time + 5,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise FetchError(f"curl timed out fetching {url}") from exc

        code_str = (proc.stdout or "").strip()
        try:
            status = int(code_str)
        except ValueError:
            status = 0
        if proc.returncode != 0 or status == 0:
            err = (proc.stderr or "").strip() or f"curl exit {proc.returncode}"
            raise FetchError(f"curl failed for {url}: {err} (http_code={code_str or '?'})")
        if status >= 400:
            raise FetchError(f"HTTP {status} for {url}")

        try:
            with open(body_path, "rb") as fh:
                body = fh.read()
        except OSError as exc:
            raise FetchError(f"curl produced no body for {url}: {exc}") from exc

        content_type = "application/octet-stream"
        try:
            with open(hdr_path, "r", encoding="utf-8", errors="replace") as fh:
                raw_hdr = fh.read()
            # After -L, multiple header blocks; use the last Content-Type.
            for match in re.finditer(r"(?im)^content-type:\s*([^\r\n]+)", raw_hdr):
                content_type = match.group(1).split(";")[0].strip().lower() or content_type
        except OSError:
            pass
        return body, content_type


def _fetch_with_httpx(
    url: str,
    timeout: float,
    verify: bool,
) -> Tuple[bytes, str]:
    import httpx

    timeout_cfg = httpx.Timeout(timeout, connect=min(10.0, timeout))
    headers = {
        "User-Agent": "NetClaw-rag-url/1.0 (+local Knowledge ingest)",
        "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
    }
    use_http2 = _httpx_http2_available()
    with httpx.Client(
        http2=use_http2,
        verify=verify,
        timeout=timeout_cfg,
        follow_redirects=True,
        headers=headers,
        trust_env=not is_private_or_local_host(url),
    ) as client:
        resp = client.get(url)
        resp.raise_for_status()
    content_type = resp.headers.get("content-type", "").split(";")[0].strip().lower()
    return resp.content, content_type


def _looks_like_http_status_error(exc: BaseException) -> bool:
    """True for definitive HTTP 4xx/5xx — do not retry alternate transports."""
    msg = str(exc)
    if re.search(r"\bHTTP [45]\d\d\b", msg):
        return True
    name = type(exc).__name__
    return name in ("HTTPStatusError",) or "Client error" in msg or "Server error" in msg


def fetch(
    url: str,
    timeout: float = 30.0,
    verify_ssl: Optional[bool] = None,
) -> Tuple[bytes, str]:
    """Fetch a URL. Returns (content_bytes, content_type). Errors verbatim.

    TLS: private-IP / localhost URLs skip cert verification by default (home-lab
    UniFi/pfSense self-signed certs). Override with verify_ssl= or RAG_URL_VERIFY_SSL.

    Transport notes (UniFi OS on :11443 is a common home-lab case):
      * Plain HTTP/1.1 often hangs after TLS (curl --http1.1 times out).
      * httpx HTTP/2 can complete SETTINGS then hang on response headers.
      * System ``curl --http2`` is reliable — used first for private/local hosts,
        and as a fallback when httpx times out on public hosts.
    """
    verify = resolve_verify_ssl(url, verify_ssl)
    private = is_private_or_local_host(url)
    has_curl = _curl_available()

    # Private/LAN: curl only when available. httpx HTTP/2 often completes TLS
    # SETTINGS then hangs forever on UniFi OS — a second attempt just doubles wait.
    # Public: httpx first, curl only on transport failure.
    if private and has_curl:
        order = ("curl",)
    elif has_curl:
        order = ("httpx", "curl")
    else:
        order = ("httpx",)

    errors: List[str] = []
    last_exc: Optional[BaseException] = None
    # UniFi OS sometimes accepts TLS then drops the first request; 1–2 quick
    # retries usually succeed (same flakiness as curl from the shell).
    attempts_per = 3 if private else 1
    for transport in order:
        for attempt in range(attempts_per):
            try:
                if transport == "curl":
                    return _fetch_with_curl(url, timeout=timeout, verify=verify)
                return _fetch_with_httpx(url, timeout=timeout, verify=verify)
            except Exception as exc:
                last_exc = exc
                errors.append(f"{transport}#{attempt + 1}: {exc}")
                if _looks_like_http_status_error(exc):
                    break
                if attempt + 1 < attempts_per:
                    import time as _time

                    _time.sleep(0.4 * (attempt + 1))
                    continue
                break

    assert last_exc is not None
    msg_u = str(last_exc).upper()
    hint = ""
    if "CERTIFICATE" in msg_u or "SSL" in msg_u:
        hint = (
            " (self-signed cert? retry with verify_ssl=false / HUD 'Allow insecure TLS', "
            "or set RAG_URL_VERIFY_SSL=false)"
        )
    elif "TIMEOUT" in msg_u or "TIMED OUT" in msg_u:
        hint = (
            " (read timeout; UniFi/nginx often need curl --http2 — "
            "ensure curl is on PATH for LAN fetches)"
        )
    detail = f"{last_exc}{hint}"
    if len(errors) > 1:
        detail = f"{detail} | attempts: {'; '.join(errors)}"
    raise FetchError(f"Could not fetch {url}: {detail}") from last_exc


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


def assess_html_quality(html: str, linked_count: int = 0) -> Dict:
    """Heuristics for JS SPA shells (UniFi OS, etc.) that look like docs but aren't.

    Returns flags used by preview so the HUD can warn before a useless ingest.
    """
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html or "", "html.parser")
    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()
    text = " ".join((soup.get_text(" ", strip=True) or "").split())
    text_len = len(text)
    raw_len = len(html or "")
    script_count = (html or "").lower().count("<script")
    # Classic SPA shell: tiny visible text, few/no <a> links, several deferred scripts
    spa_shell = (
        text_len < 120
        and linked_count == 0
        and script_count >= 2
        and raw_len < 8000
    ) or (
        text_len < 40 and linked_count <= 1 and script_count >= 1
    )
    thin = text_len < 80
    warning = None
    if spa_shell:
        warning = (
            "This looks like a JavaScript SPA shell (e.g. UniFi OS), not multi-page docs. "
            "There are no same-domain <a href> links for Preview/Crawl to follow. "
            "Ingesting this page alone yields almost no RAG content. "
            "Prefer: (1) official docs at developer.ui.com, (2) authenticated OpenAPI "
            "JSON from the controller (often /proxy/network/api/openapi — needs login), "
            "or (3) upload a vendor PDF/Markdown export."
        )
    elif thin:
        warning = (
            f"Very little extractable text ({text_len} chars). "
            "Page may be login-walled, empty, or client-rendered."
        )
    return {
        "text_chars": text_len,
        "script_tags": script_count,
        "linked_count": linked_count,
        "thin": thin,
        "spa_shell": spa_shell,
        "warning": warning,
    }


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
        "application/json": ".json",
        "application/vnd.oai.openapi+json": ".json",
        "application/openapi+json": ".json",
    }
    ext = ext_map.get(content_type, "")
    # Path already ends with .json/.yaml — keep it (OpenAPI specs).
    if not ext and stem.lower().endswith((".json", ".yaml", ".yml")):
        ext = ""
    elif ext and not stem.lower().endswith(ext):
        stem += ext
    if "." not in stem:
        stem += ".html" if content_type == "text/html" or not content_type else ".txt"
    return f"url_{digest}_{stem}"
