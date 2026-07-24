"""Unit tests for rag-mcp parsers: dispatch, size cap, hash, error paths.

Fully offline: small generated files, no fixture documents, no models.
"""

import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "mcp-servers" / "rag-mcp"))

from ingestion.parsers import (  # noqa: E402
    IngestError,
    parse_file,
    sha256_file,
)

MD_SAMPLE = """# WLC Upgrade Guide

## Prerequisites

Back up the configuration before starting. Verify boot variables.

## Upgrade Steps

Run the installer from the CLI:

```
install add file bootflash:image.bin activate commit
```

| Step | Command |
|------|---------|
| 1    | show version |
| 2    | install add |
"""

HTML_SAMPLE = """<html><head><title>Router Hardening</title>
<script>var junk = 1;</script></head>
<body><nav>menu</nav>
<h1>Router Hardening</h1>
<h2>Management Plane</h2>
<p>Disable unused services on the management plane.</p>
<pre>no ip http server
service password-encryption</pre>
<footer>copyright</footer>
</body></html>"""


@pytest.fixture()
def tmpdir_path():
    with tempfile.TemporaryDirectory() as tmp:
        yield Path(tmp)


def _write(tmpdir_path: Path, name: str, content: str) -> Path:
    p = tmpdir_path / name
    p.write_text(content, encoding="utf-8")
    return p


def test_markdown_dispatch_and_structure(tmpdir_path):
    parsed = parse_file(_write(tmpdir_path, "guide.md", MD_SAMPLE))
    assert parsed.title == "WLC Upgrade Guide"
    headings = {tuple(s.heading_path) for s in parsed.sections}
    assert ("Prerequisites",) in headings
    assert ("Upgrade Steps",) in headings
    kinds = [kind for s in parsed.sections for kind, _, _ in s.blocks]
    assert "atomic" in kinds  # fenced block and table are atomic
    assert parsed.content_hash


def test_html_dispatch_strips_boilerplate(tmpdir_path):
    parsed = parse_file(_write(tmpdir_path, "hardening.html", HTML_SAMPLE))
    assert parsed.title == "Router Hardening"
    all_text = " ".join(text for s in parsed.sections for _, text, _ in s.blocks)
    assert "Disable unused services" in all_text
    assert "menu" not in all_text and "copyright" not in all_text and "junk" not in all_text


OPENAPI_MIN = """{
  "openapi": "3.0.3",
  "info": {"title": "UniFi Network API", "version": "10.4.57", "description": "Official Network Integration API."},
  "servers": [{"url": "https://192.168.1.1/proxy/network/integration/v1"}],
  "paths": {
    "/sites": {
      "get": {
        "operationId": "listSites",
        "tags": ["Sites"],
        "summary": "List sites",
        "description": "Return all sites visible to the API key.",
        "responses": {"200": {"description": "OK"}}
      }
    },
    "/sites/{id}/devices": {
      "get": {
        "operationId": "listDevices",
        "tags": ["Devices"],
        "summary": "List devices",
        "parameters": [
          {"name": "id", "in": "path", "required": true, "description": "Site id"}
        ],
        "responses": {"200": {"description": "Device list"}}
      }
    }
  },
  "components": {"schemas": {"Site": {"type": "object"}}}
}
"""


def test_openapi_json_dispatch(tmpdir_path):
    parsed = parse_file(_write(tmpdir_path, "openapi.json", OPENAPI_MIN))
    assert "UniFi Network API" in parsed.title
    assert "10.4.57" in parsed.title
    all_text = " ".join(text for s in parsed.sections for _, text, _ in s.blocks)
    assert "GET /sites" in all_text
    assert "listSites" in all_text
    assert "List devices" in all_text
    assert "Component schemas" in all_text or "Site" in all_text


def test_generic_json_pretty_text(tmpdir_path):
    parsed = parse_file(_write(tmpdir_path, "config.json", '{"hostname": "core-sw", "vlan": 10}'))
    all_text = " ".join(text for s in parsed.sections for _, text, _ in s.blocks)
    assert "core-sw" in all_text
    assert "vlan" in all_text


def test_txt_dispatch(tmpdir_path):
    parsed = parse_file(_write(tmpdir_path, "notes.txt", "First paragraph.\n\nSecond paragraph."))
    blocks = [text for s in parsed.sections for _, text, _ in s.blocks]
    assert blocks == ["First paragraph.", "Second paragraph."]


def test_unsupported_format_rejected(tmpdir_path):
    p = tmpdir_path / "capture.pcap"
    p.write_bytes(b"\x00\x01")
    with pytest.raises(IngestError) as exc:
        parse_file(p)
    assert exc.value.code == "UNSUPPORTED_FORMAT"
    assert ".pdf" in exc.value.message  # lists supported formats


def test_size_cap_rejected_with_override_hint(tmpdir_path):
    p = tmpdir_path / "big.txt"
    p.write_bytes(b"x" * (2 * 1024 * 1024))
    with pytest.raises(IngestError) as exc:
        parse_file(p, max_mb=1)
    assert exc.value.code == "SIZE_LIMIT_EXCEEDED"
    assert "RAG_MAX_DOC_MB" in exc.value.message


def test_empty_text_parse_failed(tmpdir_path):
    with pytest.raises(IngestError) as exc:
        parse_file(_write(tmpdir_path, "empty.txt", "   \n\n  "))
    assert exc.value.code == "PARSE_FAILED"


def test_hash_stability_and_sensitivity(tmpdir_path):
    p1 = _write(tmpdir_path, "a.txt", "same content")
    p2 = _write(tmpdir_path, "b.txt", "same content")
    p3 = _write(tmpdir_path, "c.txt", "different content")
    assert sha256_file(p1) == sha256_file(p2)
    assert sha256_file(p1) != sha256_file(p3)


def test_missing_file(tmpdir_path):
    with pytest.raises(IngestError) as exc:
        parse_file(tmpdir_path / "nope.md")
    assert exc.value.code == "NOT_FOUND"


def test_legacy_format_without_soffice(tmpdir_path, monkeypatch):
    monkeypatch.setattr("shutil.which", lambda _: None)
    p = tmpdir_path / "old.doc"
    p.write_bytes(b"\xd0\xcf\x11\xe0old word doc")
    with pytest.raises(IngestError) as exc:
        parse_file(p)
    assert exc.value.code == "CONVERTER_UNAVAILABLE"
    assert "libreoffice" in exc.value.message.lower()
