"""Unit tests for URL ingestion: same-domain-only discovery, cap truncation,
scope-token enforcement. Fully offline (inline HTML, no network)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "mcp-servers" / "rag-mcp"))

from ingestion.url_fetcher import (  # noqa: E402
    discover_links,
    filename_for_url,
    page_title,
    scope_token,
    verify_scope_token,
)

BASE = "https://vendor.example/docs/guide"

HTML = """<html><head><title>WLC Guide Index</title></head><body>
<a href="/docs/chapter1">Chapter 1</a>
<a href="chapter2.html">Chapter 2</a>
<a href="https://vendor.example/docs/chapter3#section">Chapter 3</a>
<a href="https://vendor.example/docs/guide">Self link</a>
<a href="https://vendor.example/docs/chapter1">Duplicate of ch1 path? no - different path</a>
<a href="https://other.example/external">External</a>
<a href="mailto:support@vendor.example">Mail</a>
<a href="ftp://vendor.example/file">FTP</a>
</body></html>"""


def test_same_domain_depth1_discovery():
    links = discover_links(HTML, BASE, max_pages=30)
    urls = [p["url"] for p in links["linked_pages"]]
    assert "https://vendor.example/docs/chapter1" in urls
    assert "https://vendor.example/docs/chapter2.html" in urls  # relative resolved
    assert "https://vendor.example/docs/chapter3" in urls  # fragment stripped
    # Exclusions: cross-domain, non-http schemes, self-link, duplicates
    assert not any("other.example" in u for u in urls)
    assert not any(u.startswith(("mailto:", "ftp:")) for u in urls)
    assert BASE not in urls
    assert len(urls) == len(set(urls))
    assert links["truncated"] is False


def test_cap_truncation_flagged():
    many = "".join(f'<a href="/p{i}">p{i}</a>' for i in range(50))
    links = discover_links(f"<html><body>{many}</body></html>", BASE, max_pages=10)
    assert len(links["linked_pages"]) == 10
    assert links["truncated"] is True


def test_scope_token_roundtrip_and_tamper():
    linked = ["https://vendor.example/a", "https://vendor.example/b"]
    token = scope_token(BASE, linked)
    assert verify_scope_token(token, BASE, linked)
    # Order-insensitive (canonicalized), content-sensitive
    assert verify_scope_token(token, BASE, list(reversed(linked)))
    assert not verify_scope_token(token, BASE, linked + ["https://vendor.example/c"])
    assert not verify_scope_token(token, "https://vendor.example/other", linked)
    assert not verify_scope_token("", BASE, linked)
    assert not verify_scope_token("deadbeef", BASE, linked)


def test_page_title_extraction():
    assert page_title(HTML, "fallback") == "WLC Guide Index"
    assert page_title("<html><body>no title</body></html>", "fallback") == "fallback"


def test_filename_for_url_stable_and_typed():
    f1 = filename_for_url("https://vendor.example/docs/guide", "text/html")
    f2 = filename_for_url("https://vendor.example/docs/guide", "text/html")
    assert f1 == f2  # deterministic
    assert f1.endswith(".html")
    fpdf = filename_for_url("https://vendor.example/files/manual.pdf", "application/pdf")
    assert fpdf.endswith(".pdf")
    froot = filename_for_url("https://vendor.example/", "text/html")
    assert froot.endswith(".html")
