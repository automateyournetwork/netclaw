#!/usr/bin/env python3
"""Crawl an API / documentation website and produce a PDF (and optional Markdown)
for NetClaw RAG upload via the HUD Knowledge panel.

Designed for vendor docs that only exist as multi-page HTML (e.g. UniFi Network
Integration API on a controller or developer portal) with no official PDF.

Examples
--------
  # Public site, same-domain crawl, depth 2, max 80 pages
  python3 scripts/docs-site-to-pdf.py \\
    --start-url "https://developer.ui.com/..." \\
    --out ~/Downloads/unifi-network-api.pdf

  # Local UniFi controller docs (self-signed TLS)
  python3 scripts/docs-site-to-pdf.py \\
    --start-url "https://192.168.100.10:11443/unifi-api/network" \\
    --insecure --max-pages 100 --depth 3 \\
    --out ~/.openclaw/rag/intake/unifi-network-api.pdf

  # Also write Markdown (often chunks better in RAG)
  python3 scripts/docs-site-to-pdf.py ... --markdown

Then: HUD Knowledge → type **vendor** → Upload file (or leave in intake and
rag_ingest the path).

Dependencies: httpx, beautifulsoup4, fpdf2 (in netclaw .venv).
"""

from __future__ import annotations

import argparse
import re
import sys
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List, Optional, Set, Tuple
from urllib.parse import urldefrag, urljoin, urlparse, urlunparse

try:
    import httpx
except ImportError:
    print("Need httpx: pip install httpx", file=sys.stderr)
    sys.exit(1)

try:
    from bs4 import BeautifulSoup
except ImportError:
    print("Need beautifulsoup4: pip install beautifulsoup4", file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
# Crawl helpers
# ---------------------------------------------------------------------------

SKIP_EXT = (
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".ico",
    ".css", ".js", ".map", ".woff", ".woff2", ".ttf", ".eot",
    ".zip", ".gz", ".tgz", ".mp4", ".webm", ".mp3",
)


def normalize_url(url: str) -> str:
    url = urldefrag(url)[0].strip()
    p = urlparse(url)
    # drop default ports, trailing slash consistency (keep path root slash)
    netloc = p.netloc.lower()
    path = p.path or "/"
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")
    return urlunparse((p.scheme.lower(), netloc, path, "", p.query, ""))


def same_site(a: str, b: str, allow_subdomains: bool) -> bool:
    ha, hb = urlparse(a).netloc.lower(), urlparse(b).netloc.lower()
    if ha == hb:
        return True
    if not allow_subdomains:
        return False
    return ha.endswith("." + hb) or hb.endswith("." + ha)


def is_skippable(url: str) -> bool:
    path = urlparse(url).path.lower()
    return any(path.endswith(ext) for ext in SKIP_EXT)


def _rag_url_fetcher():
    """Import rag-mcp url_fetcher (curl+httpx) for UniFi-safe LAN fetches."""
    rag_root = Path(__file__).resolve().parents[1] / "mcp-servers" / "rag-mcp"
    rag_s = str(rag_root)
    if rag_s not in sys.path:
        sys.path.insert(0, rag_s)
    from ingestion import url_fetcher as uf  # type: ignore

    return uf


def resolve_verify(url: str, insecure: bool) -> bool:
    if insecure:
        return False
    # Match rag-mcp home-lab default: private hosts skip verify
    try:
        return _rag_url_fetcher().resolve_verify_ssl(url, verify_ssl=None)
    except Exception:
        return True


def fetch_html(
    client: Optional["httpx.Client"],
    url: str,
    *,
    verify_ssl: Optional[bool] = None,
    use_rag_fetch: bool = False,
) -> Tuple[str, str]:
    """Returns (final_url, html_text).

    When use_rag_fetch is True (default for private/LAN starts), use rag-mcp's
    fetch() which prefers system curl --http2 — UniFi OS hangs on httpx.
    """
    if use_rag_fetch or client is None:
        uf = _rag_url_fetcher()
        content, ctype = uf.fetch(url, timeout=45.0, verify_ssl=verify_ssl)
        if ctype and "html" not in ctype and "text/" not in ctype and "json" not in ctype:
            raise ValueError(f"skip non-text content-type {ctype}")
        if "json" in (ctype or ""):
            text = content.decode("utf-8", errors="replace")
            title = urlparse(url).path.rsplit("/", 1)[-1] or "api.json"
            html = (
                f"<html><head><title>{title}</title></head>"
                f"<body><pre>{_escape(text)}</pre></body></html>"
            )
            return url, html
        return url, content.decode("utf-8", errors="replace")

    r = client.get(url, follow_redirects=True)
    r.raise_for_status()
    ctype = (r.headers.get("content-type") or "").split(";")[0].strip().lower()
    if ctype and "html" not in ctype and "text/" not in ctype and "json" not in ctype:
        raise ValueError(f"skip non-text content-type {ctype}")
    # JSON OpenAPI/Swagger — wrap as preformatted "html" for extraction
    if "json" in ctype:
        text = r.text
        title = urlparse(url).path.rsplit("/", 1)[-1] or "api.json"
        html = f"<html><head><title>{title}</title></head><body><pre>{_escape(text)}</pre></body></html>"
        return str(r.url), html
    return str(r.url), r.text


def _escape(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def extract_main_text(html: str, base_url: str) -> Tuple[str, str, List[str]]:
    """Return (title, plain_text, outbound_same_doc_links)."""
    soup = BeautifulSoup(html, "html.parser")

    # Drop noise
    for tag in soup(["script", "style", "noscript", "svg", "iframe", "nav", "footer", "header"]):
        # keep first header if it's the only h1 source — remove chrome headers
        tag.decompose()

    title = ""
    if soup.title and soup.title.string:
        title = soup.title.string.strip()
    if not title:
        h1 = soup.find(["h1", "h2"])
        if h1:
            title = h1.get_text(" ", strip=True)
    if not title:
        title = urlparse(base_url).path or base_url

    # Prefer main content containers when present
    root = (
        soup.find("main")
        or soup.find("article")
        or soup.find(attrs={"role": "main"})
        or soup.find(class_=re.compile(r"(content|markdown|doc|swagger|openapi|redoc)", re.I))
        or soup.body
        or soup
    )

    lines: List[str] = []
    for el in root.find_all(["h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "pre", "code", "td", "th"]):
        text = el.get_text(" ", strip=True)
        if not text:
            continue
        name = el.name.lower()
        if name.startswith("h"):
            level = int(name[1])
            lines.append("")
            lines.append("#" * level + " " + text)
            lines.append("")
        elif name == "pre":
            lines.append("")
            lines.append(text)
            lines.append("")
        elif name == "li":
            lines.append(f"- {text}")
        else:
            lines.append(text)

    # Dedup consecutive blanks / identical lines
    cleaned: List[str] = []
    prev = None
    for line in lines:
        if line == prev and line.strip() == "":
            continue
        if line == prev and len(line) < 200:
            continue
        cleaned.append(line)
        prev = line

    plain = "\n".join(cleaned).strip()
    if len(plain) < 40:
        # fallback: full body text
        plain = root.get_text("\n", strip=True)

    links: List[str] = []
    for a in soup.find_all("a", href=True):
        href = urljoin(base_url, a["href"])
        links.append(href)

    return title, plain, links


@dataclass
class PageDoc:
    url: str
    title: str
    text: str
    depth: int


@dataclass
class CrawlResult:
    pages: List[PageDoc] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


def crawl(
    start_url: str,
    *,
    max_pages: int = 80,
    max_depth: int = 2,
    delay_s: float = 0.35,
    insecure: bool = False,
    allow_subdomains: bool = False,
    path_prefix: Optional[str] = None,
    extra_headers: Optional[dict] = None,
) -> CrawlResult:
    start = normalize_url(start_url)
    origin = f"{urlparse(start).scheme}://{urlparse(start).netloc}"
    prefix = path_prefix
    if prefix is None:
        # default: stay under the start path's directory
        p = urlparse(start).path or "/"
        if "." in p.rsplit("/", 1)[-1]:
            prefix = p.rsplit("/", 1)[0] or "/"
        else:
            prefix = p if p.endswith("/") else (p + "/" if p != "/" else "/")
        # for SPA roots like /unifi-api/network keep that path stem
        if not prefix.endswith("/"):
            # allow siblings under same parent folder
            prefix = prefix.rsplit("/", 1)[0] + "/" if "/" in prefix.strip("/") else "/"

    verify = resolve_verify(start, insecure)
    # Explicit False when --insecure; None lets rag-mcp auto-skip verify on RFC1918.
    verify_ssl_arg: Optional[bool] = False if insecure or verify is False else None
    headers = {
        "User-Agent": "NetClaw-docs-site-to-pdf/1.0 (+local RAG ingest; contact: operator)",
        "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
    }
    if extra_headers:
        headers.update(extra_headers)

    result = CrawlResult()
    seen: Set[str] = set()
    q: deque[Tuple[str, int]] = deque([(start, 0)])

    # LAN gear (UniFi OS): use rag-mcp fetch (curl --http2 first). httpx hangs after TLS
    # SETTINGS on many UniFi OS builds even with HTTP/2 enabled.
    use_rag_fetch = False
    try:
        uf = _rag_url_fetcher()
        use_rag_fetch = uf.is_private_or_local_host(start) or insecure
    except Exception:
        use_rag_fetch = insecure

    def _crawl_loop(client: Optional[httpx.Client]) -> None:
        while q and len(result.pages) < max_pages:
            url, depth = q.popleft()
            url = normalize_url(url)
            if url in seen:
                continue
            seen.add(url)
            if not same_site(start, url, allow_subdomains):
                continue
            if is_skippable(url):
                continue
            path = urlparse(url).path or "/"
            # Allow the start URL always; otherwise require path under prefix
            if url != start and prefix and prefix != "/" and not path.startswith(prefix.rstrip("/") ):
                # also allow if path startswith prefix without trailing rules
                if not path.startswith(prefix) and not path.startswith(prefix.rstrip("/")):
                    continue

            try:
                final_url, html = fetch_html(
                    client,
                    url,
                    verify_ssl=verify_ssl_arg,
                    use_rag_fetch=use_rag_fetch,
                )
                final_url = normalize_url(final_url)
                title, text, out_links = extract_main_text(html, final_url)
                # SPA shells often have <20 useful chars; also reject short chrome-only pages
                if len(text.strip()) < 80:
                    result.errors.append(f"thin content ({len(text.strip())} chars): {url}")
                    print(f"  ~ thin ({len(text.strip())} chars) {url}", flush=True)
                else:
                    result.pages.append(PageDoc(url=final_url, title=title, text=text, depth=depth))
                    print(f"[{len(result.pages):3d}/{max_pages}] d={depth} {title[:60]!r}", flush=True)

                if depth < max_depth:
                    for link in out_links:
                        n = normalize_url(link)
                        if n not in seen and same_site(start, n, allow_subdomains) and not is_skippable(n):
                            q.append((n, depth + 1))
            except Exception as exc:
                result.errors.append(f"{url}: {exc}")
                print(f"  ! {url}: {exc}", flush=True)
            if delay_s > 0:
                time.sleep(delay_s)

    if use_rag_fetch:
        print("  transport=rag-fetch (curl --http2 preferred for LAN/UniFi)", flush=True)
        _crawl_loop(None)
    else:
        try:
            import h2  # noqa: F401

            use_http2 = True
        except ImportError:
            use_http2 = False
        with httpx.Client(
            http2=use_http2,
            timeout=httpx.Timeout(45.0, connect=10.0),
            verify=verify,
            headers=headers,
            trust_env=False if verify is False else True,
        ) as client:
            _crawl_loop(client)

    return result


# ---------------------------------------------------------------------------
# Writers
# ---------------------------------------------------------------------------

def write_markdown(pages: Iterable[PageDoc], out_path: Path, start_url: str) -> None:
    lines = [
        f"# Documentation crawl",
        f"",
        f"- Source: {start_url}",
        f"- Captured: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        f"- Pages: {sum(1 for _ in pages) if not isinstance(pages, list) else len(list(pages))}",
        f"",
    ]
    # re-materialize if generator was consumed — callers pass list
    page_list = list(pages) if not isinstance(pages, list) else pages
    lines[4] = f"- Pages: {len(page_list)}"
    for i, p in enumerate(page_list, 1):
        lines.append("---")
        lines.append(f"")
        lines.append(f"## {i}. {p.title}")
        lines.append(f"")
        lines.append(f"_URL: {p.url}_")
        lines.append(f"")
        lines.append(p.text)
        lines.append(f"")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")


def write_pdf(pages: List[PageDoc], out_path: Path, start_url: str) -> None:
    try:
        from fpdf import FPDF
    except ImportError:
        print("Need fpdf2: pip install fpdf2", file=sys.stderr)
        sys.exit(1)

    class DocPDF(FPDF):
        def footer(self):
            self.set_y(-12)
            self.set_font("Helvetica", size=8)
            self.set_text_color(120, 120, 120)
            self.cell(0, 8, f"Page {self.page_no()}/{{nb}}  |  NetClaw docs-site-to-pdf", align="C")

    pdf = DocPDF()
    pdf.alias_nb_pages()
    pdf.set_margins(15, 15, 15)
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()
    usable = pdf.epw  # effective page width inside margins

    def write_line(text: str, h: float = 5.0) -> None:
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(usable, h, text)

    # Helvetica can't do all unicode — sanitize
    def safe(s: str) -> str:
        repl = {
            "\u2013": "-", "\u2014": "-", "\u2018": "'", "\u2019": "'",
            "\u201c": '"', "\u201d": '"', "\u2026": "...", "\u00a0": " ",
            "\u2192": "->", "\u2190": "<-", "\u00b7": "*",
        }
        for a, b in repl.items():
            s = s.replace(a, b)
        return s.encode("latin-1", errors="replace").decode("latin-1")

    pdf.set_font("Helvetica", "B", 16)
    write_line("Documentation crawl", 8)
    pdf.ln(2)
    pdf.set_font("Helvetica", size=10)
    write_line(safe(f"Source: {start_url}"))
    write_line(f"Captured: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    write_line(f"Pages: {len(pages)}")
    pdf.ln(4)

    for i, p in enumerate(pages, 1):
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 13)
        write_line(safe(f"{i}. {p.title}"), 7)
        pdf.set_font("Helvetica", "I", 8)
        pdf.set_text_color(80, 80, 80)
        write_line(safe(p.url), 4)
        pdf.set_text_color(0, 0, 0)
        pdf.ln(2)
        pdf.set_font("Helvetica", size=9)
        body = safe(p.text)
        for para in body.split("\n"):
            if not para.strip():
                pdf.ln(3)
                continue
            para = re.sub(r"(\S{90})", r"\1 ", para)
            try:
                write_line(para, 4.2)
            except Exception:
                write_line(para[:500] + "...", 4.2)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(out_path))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(
        description="Crawl a documentation website → PDF (and optional Markdown) for RAG"
    )
    ap.add_argument("--start-url", "-u", required=True, help="Seed documentation URL")
    ap.add_argument(
        "--out", "-o",
        default=None,
        help="Output PDF path (default: ./docs-crawl-<host>.pdf)",
    )
    ap.add_argument("--max-pages", type=int, default=80, help="Max pages to fetch (default 80)")
    ap.add_argument("--depth", type=int, default=2, help="Max link depth from start (default 2)")
    ap.add_argument("--delay", type=float, default=0.35, help="Delay between requests (seconds)")
    ap.add_argument("--insecure", action="store_true", help="Skip TLS certificate verification")
    ap.add_argument("--allow-subdomains", action="store_true", help="Follow links on subdomains")
    ap.add_argument(
        "--path-prefix",
        default=None,
        help="Only crawl paths under this prefix (default: directory of start URL)",
    )
    ap.add_argument("--markdown", action="store_true", help="Also write a .md alongside the PDF")
    ap.add_argument(
        "--header",
        action="append",
        default=[],
        help="Extra HTTP header, e.g. --header 'X-API-Key: secret' (repeatable)",
    )
    args = ap.parse_args()

    start = args.start_url.strip()
    if not re.match(r"^https?://", start, re.I):
        print("start-url must be http(s)", file=sys.stderr)
        return 2

    host = urlparse(start).netloc.replace(":", "_")
    out_pdf = Path(args.out).expanduser() if args.out else Path(f"docs-crawl-{host}.pdf")
    if out_pdf.suffix.lower() != ".pdf":
        out_pdf = out_pdf.with_suffix(".pdf")

    headers = {}
    for h in args.header:
        if ":" in h:
            k, v = h.split(":", 1)
            headers[k.strip()] = v.strip()

    print(f"Crawl start: {start}")
    print(f"  max_pages={args.max_pages} depth={args.depth} insecure={args.insecure}")
    result = crawl(
        start,
        max_pages=args.max_pages,
        max_depth=args.depth,
        delay_s=args.delay,
        insecure=args.insecure,
        allow_subdomains=args.allow_subdomains,
        path_prefix=args.path_prefix,
        extra_headers=headers or None,
    )

    if not result.pages:
        print("No pages captured. Errors:", file=sys.stderr)
        for e in result.errors[:20]:
            print(f"  {e}", file=sys.stderr)
        return 1

    print(f"\nWriting PDF ({len(result.pages)} pages) → {out_pdf}")
    write_pdf(result.pages, out_pdf, start)
    print(f"  size: {out_pdf.stat().st_size // 1024} KiB")

    if args.markdown:
        md_path = out_pdf.with_suffix(".md")
        write_markdown(result.pages, md_path, start)
        print(f"Writing Markdown → {md_path} ({md_path.stat().st_size // 1024} KiB)")

    if result.errors:
        print(f"\n{len(result.errors)} fetch warnings/errors (first 10):")
        for e in result.errors[:10]:
            print(f"  {e}")

    print(
        "\nNext: HUD Knowledge → doc type **vendor** → Upload file:\n"
        f"  {out_pdf.resolve()}\n"
        "Or: rag_ingest with that file_path."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
