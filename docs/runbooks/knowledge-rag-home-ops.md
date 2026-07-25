# Knowledge RAG for NetClaw Convergence ops

## What it is

The Visual HUD **Knowledge** panel uploads documents into the offline RAG store
(`~/.openclaw/rag`, collection `documents`). That same corpus is what **Border**
and **guardian-claw** search via `rag-mcp` tools.

## Supported formats

| Format | Notes |
|--------|--------|
| PDF, MD, HTML, TXT | Native parsers |
| **JSON** | OpenAPI/Swagger → per-endpoint sections; other JSON pretty-printed as text |
| DOCX, XLSX, PPTX, VSDX | Python parsers |
| DOC, XLS, PPT, VSD | LibreOffice headless when installed |

**Why JSON was missing at first:** Feature 062 v1 targeted human documents
(PDF/MD/HTML/office). Machine specs (OpenAPI) were out of that initial list —
not a security block. OpenAPI is now first-class for vendor API manuals.

## Operator workflow

1. Expand **Knowledge** (desktop: **drag the header** to move; **corner** to resize;
   ↺ resets layout).
2. Set type:
   - **vendor** — UniFi OpenAPI, pfSense docs, Cisco switch guides
   - **install-guide** / **standard** / **customer** — MoPs and site policy
3. Ingest via:
   - **Upload file** (PDF/MD/JSON/…)
   - **Preview URL** → **Ingest page** (single URL; OpenAPI JSON works)
   - **Crawl site to RAG** (multi-page *static* HTML docs — not JS SPAs)
4. Wait until status is **ready** (high chunk counts ≈ real manual).
5. Ask NetClaw (or let alert-triage run) questions that need vendor procedure —
   investigators should call `rag_search` on `documents`.

### Documents vs Snapshots

| Section | Meaning |
|---------|---------|
| **Documents** | Vendor PDFs, OpenAPI, site crawls you uploaded |
| **Snapshots** | Past alert *investigations* (WifiDegraded…) — **not** crawl output |

Green **ready** with few chunks often means a thin/JS-only page was ingested.

## UniFi Network API → Knowledge (this house)

| Source | Result |
|--------|--------|
| `https://192.168.100.10:11443/unifi-api/network` | SPA shell only — 0 links, not useful for RAG |
| `…/proxy/network/api-docs/integration.json` + API key | **Hangs / empty body** on UOS Server (Network 10.4.57) |
| `…/proxy/network/integration/v1/*` + `X-API-KEY` | Live API works (`/info`, `/sites`, devices…) — data, not docs |
| **`https://developer.ui.com/network/v10.4.57/openapi.json`** | **Preferred** — full OpenAPI for Network 10.4.57 |

```text
# HUD: type vendor → paste OpenAPI URL → Ingest page
https://developer.ui.com/network/v10.4.57/openapi.json

# Or download + upload
curl -sS -o unifi-network-v10.4.57-openapi.json \
  https://developer.ui.com/network/v10.4.57/openapi.json
```

### LAN TLS / fetch quirks (implemented in rag-mcp)

- Private/RFC1918 hosts: cert verify **off** by default (`RAG_URL_VERIFY_SSL=auto`).
- HUD **Allow insecure TLS** forces `verify_ssl=false`.
- UniFi OS often hangs on HTTP/1.1; **HTTP/2** required.
- httpx can hang after TLS SETTINGS on UniFi; **LAN fetches use system `curl --http2`** first (with retries).
- Preview returns `spa_shell` / `thin` warnings for JS chrome pages.

### Multi-page HTML docs (not UniFi SPA)

```bash
./.venv/bin/python3 scripts/docs-site-to-pdf.py \
  --start-url "https://developer.ui.com/network/" \
  --max-pages 80 --depth 2 --delay 0.3 --markdown \
  --out ~/.openclaw/rag/intake/unifi-network-portal.pdf
```

For local self-signed gear only: add `--insecure`. SPA roots still yield thin pages.

## Investigator wiring

| Consumer | Access |
|----------|--------|
| Border `rag-mcp` | `openclaw.json` → `RAG_DATA_DIR` |
| guardian-claw | Scoped config + `.env` `RAG_DATA_DIR=~/.openclaw/rag` (same path) |
| Skills | `alert-triage`, `wifi-diagnosis`, `monitoring-onboard`, `rag` |

Search examples:

```text
rag_search(query="UniFi Integration API list devices", collection="documents")
rag_search(query="pfSense gateway group", collection="documents", filters={doc_type: "vendor"})
rag_search(query="WifiHighTxRetries Basement", collection="investigations")  # prior cases
```

## Ensure member can see HUD uploads

```bash
grep RAG_DATA_DIR migration-staging/members/guardian-claw/.env
# Should be: RAG_DATA_DIR=/home/ubuntu/.openclaw/rag  (or $HOME/.openclaw/rag)
systemctl --user restart netclaw-member-*-guardian-claw
```

`scripts/ensure-guardian-claw.py` seeds `RAG_DATA_DIR` on new members.
`in2n-profiles` includes `RAG_` in the network-guardian env slice.

## Env knobs

| Variable | Default | Purpose |
|----------|---------|---------|
| `RAG_DATA_DIR` | `~/.openclaw/rag` | Corpus root |
| `RAG_URL_VERIFY_SSL` | `auto` | `auto` skips verify for private IPs; `false` always insecure |
| `RAG_MAX_DOC_MB` / `RAG_MAX_DOC_PAGES` | 100 / 1000 | Caps |
| `RAG_CRAWL_MAX_PAGES` | 30 | Depth-1 URL preview link cap |
