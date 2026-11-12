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


def test_download_cap_counts_decoded_bytes_and_closes_stream(monkeypatch):
    import gzip
    import httpx
    import pytest
    from ingestion.url_fetcher import fetch, FetchError

    class Stream(httpx.SyncByteStream):
        def __init__(self, chunks):
            self.chunks = chunks
            self.closed = False
            self.reads = 0

        def __iter__(self):
            for chunk in self.chunks:
                self.reads += 1
                yield chunk

        def close(self):
            self.closed = True

    # No Content-Length: enforce actual bytes; do not consume the rest on rejection.
    stream = Stream([b'abc', b'def', b'should not be read'])
    with httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200, stream=stream))) as client:
        monkeypatch.setattr(httpx, 'stream', client.stream)
        with pytest.raises(FetchError, match='exceeds'):
            fetch(BASE, max_bytes=5)
    assert stream.closed and stream.reads == 2

    # A small compressed response must not bypass the decoded-size limit.
    stream = Stream([gzip.compress(b'a' * 200)])
    with httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200, headers={'content-encoding':'gzip'}, stream=stream))) as client:
        monkeypatch.setattr(httpx, 'stream', client.stream)
        with pytest.raises(FetchError, match='exceeds'):
            fetch(BASE, max_bytes=100)
    assert stream.closed

    stream = Stream([b'abc', b'de'])
    with httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200, headers={'content-type':'text/plain; charset=utf-8'}, stream=stream))) as client:
        monkeypatch.setattr(httpx, 'stream', client.stream)
        assert fetch(BASE, max_bytes=5) == (b'abcde', 'text/plain')
    assert stream.closed


def test_html_preview_uses_visible_text_and_scripts():
    from ingestion.url_fetcher import preview_html

    shell = '<head><title>Documentation</title></head><body><script src="app.js"></script></body>'
    preview = preview_html(shell, BASE, 5)
    assert preview["title"] == "Documentation"
    assert preview["text_chars"] == 0
    assert preview["thin"] and preview["spa_shell"]
    assert "OpenAPI" in preview["warning"]
    assert not preview_html("<p>Maintenance</p>", BASE, 5)["spa_shell"]
    article = preview_html("<script></script><p>" + "body " * 60 + "</p>", BASE, 5)
    assert not article["spa_shell"] and article["warning"] is None


def test_json_url_media_types():
    assert filename_for_url(BASE + "/openapi.json", "text/plain").endswith(".json")
    for media in ("application/json", "application/vnd.oai.openapi+json"):
        assert filename_for_url(BASE, media).endswith(".json")


def test_explicit_unverified_transport_rejects_redirect(monkeypatch):
    import httpx
    import pytest
    from ingestion.url_fetcher import FetchError, fetch

    def stream(method, url, **kwargs):
        assert kwargs.pop("verify") is False
        return client.stream(method, url, **kwargs)

    def redirect(request):
        assert str(request.url) == BASE
        return httpx.Response(301, headers={"Location": "https://other.example"})

    with httpx.Client(transport=httpx.MockTransport(redirect)) as client:
        monkeypatch.setattr(httpx, "stream", stream)
        with pytest.raises(FetchError, match="301"):
            fetch(BASE, verify_ssl=False)


def test_local_http2_transport(tmp_path):
    """Loopback-only TLS endpoint requiring HTTP/2, with no HTTP/1 fallback."""
    import shutil
    import subprocess
    import pytest
    from ingestion.local_https import _http2_curl
    from ingestion.url_fetcher import FetchError, fetch

    if not (_http2_curl() and shutil.which("node") and shutil.which("openssl")):
        pytest.skip("requires HTTP/2-capable curl, node and openssl")
    subprocess.run(["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes",
                    "-subj", "/CN=localhost", "-addext", "subjectAltName=DNS:localhost",
                    "-days", "1", "-keyout", "key.pem", "-out", "cert.pem"],
                   cwd=tmp_path, check=True, capture_output=True)
    fixture = """
const fs = require('node:fs');
const server = require('node:http2').createSecureServer({
  key: fs.readFileSync('key.pem'), cert: fs.readFileSync('cert.pem')
});
server.on('stream', (stream, headers) => {
  if (headers[':path'] === '/redirect') {
    stream.respond({':status': 302, location: '/openapi'});
    return stream.end();
  }
  if (headers[':path'] === '/oversize') {
    stream.respond({'content-encoding': 'gzip'});
    return stream.end(require('node:zlib').gzipSync(Buffer.alloc(8192)));
  }
  stream.respond({'content-type': 'application/json; charset=utf-8'});
  stream.end('{"openapi":"3.1.0"}');
});
server.listen(0, '127.0.0.1', () => console.log(server.address().port));
"""
    with subprocess.Popen(["node", "-e", fixture], cwd=tmp_path,
                          stdout=subprocess.PIPE, text=True) as server:
        try:
            import select
            assert select.select([server.stdout], [], [], 5)[0], "HTTP/2 fixture failed to start"
            url = f"https://localhost:{int(server.stdout.readline())}"
            with pytest.raises(FetchError):
                fetch(url, timeout=5)
            assert fetch(url, timeout=5, verify_ssl=False) == (b'{"openapi":"3.1.0"}', 'application/json')
            with pytest.raises(FetchError, match="302"):
                fetch(url + "/redirect", timeout=5, verify_ssl=False)
            with pytest.raises(FetchError, match="exceeds"):
                fetch(url + "/oversize", timeout=5, verify_ssl=False, max_bytes=100)
        finally:
            server.terminate()
