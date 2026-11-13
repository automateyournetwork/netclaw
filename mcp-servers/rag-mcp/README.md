# rag-mcp — NetClaw Agentic RAG Knowledge Base

Fully **offline, free, local** document knowledge base for NetClaw (Feature 062). Users teach NetClaw by uploading documents — vendor guides, standards, customer design docs, install guides — via Slack attachment, the HUD Knowledge panel, or URL. Retrieval is agentic: NetClaw decides when to search, critiques results, refines queries within a budget, and cites every claim.

**This is not memory.** rag-mcp stores what USERS upload (`~/.openclaw/rag/`); the Memory MCP stores NetClaw's own experience (`~/.openclaw/memory/`). Neither writes into the other.

## Tools (10)

| Tool | Description | Key parameters |
|------|-------------|----------------|
| `rag_ingest` | Ingest a document file on disk | `file_path`, `doc_type` (vendor\|standard\|customer\|install-guide\|other), `title?`, `version?`, `source?` |
| `rag_ingest_base64` | Ingest a base64-encoded file (Slack attachment path) | `filename`, `content_base64`, `doc_type?`, `title?` |
| `rag_ingest_url` | Two-phase URL ingestion with crawl-scope gate | `url`, `mode` (preview\|ingest), `include_linked?`, `scope_token?`, `verify_ssl=true` |
| `rag_search` | Hybrid search: dense + BM25 → RRF fusion → local rerank. `investigations` / `snapshots` / `cases` search every ready snapshot; `all` / `*` adds the document corpus; any other name is that collection only | `query`, `k=5`, `collection`, `filters?` (doc_type/document_id/title/date range), `round?`, `sub_query_id?` |
| `rag_list` | All documents + snapshots (separate) with full metadata | `kind` (documents\|snapshots\|all) |
| `rag_stats` | Corpus totals + rolling retrieval telemetry | — |
| `rag_update_metadata` | Edit doc_type / title / version | `document_id`, fields |
| `rag_delete` | Remove a document from all indexes (HIIL-gated) | `document_id`, `confirmed` |
| `rag_reindex` | Re-chunk/re-embed from the retained original (HIIL-gated) | `document_id`, `confirmed` |
| `rag_snapshot` | OPT-IN vectorization of live output, secret-scrubbed | `label`, `content`, `source_description`, `devices?`, `commands?` |

All responses use the envelope `{"success": bool, "data": ..., "error": {"code", "message"}}`. Error codes: `UNSUPPORTED_FORMAT`, `SIZE_LIMIT_EXCEEDED`, `PARSE_FAILED`, `CONVERTER_UNAVAILABLE`, `NOT_FOUND`, `SCOPE_TOKEN_INVALID`, `MODELS_NOT_CACHED`, `FETCH_FAILED`.

## Supported formats

- **Native**: PDF (pymupdf — pages, TOC headings, tables), Markdown, HTML, TXT, JSON (OpenAPI/Swagger operations get method and path headings)
- **Modern office**: DOCX, XLSX, PPTX, VSDX (Python parsers)
- **Legacy office**: DOC, XLS, PPT, VSD via LibreOffice headless (`soffice`) conversion — optional system package; other formats work without it

HTML URL previews include `text_chars`, `thin`, `spa_shell`, and an optional `warning` about client-rendered or nearly empty pages. Local HTTPS appliances use system curl with HTTP/2 negotiation when available. The ordinary HTTP client handles other URLs. By default both transports verify certificates. An explicit `verify_ssl=false` applies to this call and disables redirect following.

## Retrieval pipeline

1. Dense leg: ChromaDB cosine search with `BAAI/bge-small-en-v1.5` embeddings (BGE query-instruction prefix)
2. Keyword leg: BM25 (`rank_bm25`) with a networking-aware tokenizer — `Gi0/0/1`, `192.0.2.0/24`, `CVE-2026-1234` stay whole tokens
3. Reciprocal rank fusion (k=60), top-20
4. Local cross-encoder rerank (`cross-encoder/ms-marco-MiniLM-L-6-v2`) to top-k; disable via `RAG_RERANK_ENABLED=false`
5. Sub-floor results flagged `low_confidence: true` — never dropped
6. Every result carries a preformatted citation: `[Title §section, p.N — ingested YYYY-MM-DD]` (chunk IDs stay in the retrieval log)

## Chunking

Structure-aware: heading boundaries first, then paragraphs, 400–800 tokens (embedder tokenizer) with ~12% overlap. Fenced code/CLI/config blocks and tables are atomic — never split; oversized atomic blocks become standalone chunks. Every chunk is prefixed with a `Document Title > Chapter > Section` breadcrumb before embedding.

## Snapshots

`rag_snapshot` is the ONLY sanctioned RAG use of live data — explicit human request + scope confirmation, never automatic. Content passes a secret scrubber (Cisco type 5/7/8/9, enable/user secrets, SNMP communities, TACACS/RADIUS keys, routing auth keys, pre-shared keys, Juniper `$9$`, adjacent usernames → `<REDACTED:type>`, per-type counts with explicit zeros) before vectorization into a new `snapshot_<label>_<ISO8601>` collection. Retrieval from snapshots always includes `age_human` staleness ("captured 2026-07-16 14:02 UTC — 31 days ago"); snapshots older than `RAG_SNAPSHOT_WARN_DAYS` (90) are flagged stale, never auto-deleted.

`rag_search` does not treat `investigations` as a literal collection name. `investigations`, `snapshots`, and `cases` search registry rows with `kind=snapshot`, `ingest_status=ready`, and a collection — the newest `RAG_INVESTIGATION_MAX_COLLECTIONS` (50) of them by `ingest_ts`. `ingested_after` / `ingested_before` select snapshot rows before that cap, so a date range reaches older snapshots; otherwise name an older collection literally. The response reports `collections_searched` and `collections_skipped` (matching snapshots left out by the cap) as counts, and the cap is also logged. At most `2k` fused candidates per collection go to the reranker, so with the cross-encoder on one alias search reranks up to cap × 2k candidates on CPU (500 at the defaults with `k=5`). Hits are merged by rerank score. With reranking off, passthrough scores are dense cosine and BM25-only exact matches would sink, so hits are merged by fused (RRF) score instead. RRF is rank-based: every collection's top hit scores 2/61 when both legs rank it first, so the merge interleaves collections by rank, not by how well each one matches. The top `k` are returned. Each hit includes the source collection. `all` and `*` search `documents` plus those snapshots. Any other collection name is searched literally. When no investigation snapshots are indexed, the snapshot aliases return the usual empty-corpus shape and say so. A missing or unreadable snapshot collection is skipped; when none can be read, or `documents` cannot be read on `all` / `*`, the result is `STORAGE_UNAVAILABLE`. The retrieval log records the alias and the collections searched (`investigations -> snapshot_a,snapshot_b`). `ingested_after` / `ingested_before` compare each chunk's `ingest_ts` (when it was indexed), for snapshots too — not the snapshot's `capture_ts`.

## Environment variables (no credentials)

| Variable | Default | Purpose |
|----------|---------|---------|
| `RAG_DATA_DIR` | `~/.openclaw/rag` | Persistent store root |
| `RAG_EMBEDDING_MODEL` | `BAAI/bge-small-en-v1.5` | Upgrade: `BAAI/bge-base-en-v1.5` |
| `RAG_RERANKER_MODEL` | `cross-encoder/ms-marco-MiniLM-L-6-v2` | Upgrade: `BAAI/bge-reranker-base` |
| `RAG_RERANK_ENABLED` | `true` | `false` for low-resource hosts |
| `RAG_RELEVANCE_FLOOR` | `0.3` | low_confidence threshold |
| `RAG_MAX_DOC_MB` / `RAG_MAX_DOC_PAGES` | `100` / `1000` | Per-document caps |
| `RAG_CRAWL_MAX_PAGES` | `30` | Depth-1 preview bound |
| `RAG_SNAPSHOT_WARN_DAYS` | `90` | Staleness warning |
| `RAG_MAX_ROUNDS` | `3` | Retrieval rounds per sub-query |
| `RAG_INVESTIGATION_MAX_COLLECTIONS` | `50` | Newest snapshot collections one alias search covers |

## Storage layout

```
~/.openclaw/rag/
├── rag.db       # SQLite: document registry, retrieval log, schema version
├── chroma/      # ChromaDB PersistentClient (dense vectors)
├── bm25/        # <collection>.pkl keyword indexes
├── sources/     # retained originals (basis for rag_reindex)
└── intake/      # upload landing zone (Slack base64 / HUD multipart / URL)
```

Ingestion is atomic per document: chunks commit to both indexes before the registry row flips to `ready`; interrupted ingests are swept to `error` at startup with partial entries purged.

## Transport & install

- **Transport**: stdio (FastMCP), JSON-RPC lifecycle
- **Install**: `pip3 install -e mcp-servers/rag-mcp` (done by the NetClaw modular installer, component `rag-mcp`, default-on). Models (~250 MB total) download once at install; the system is fully offline afterwards. Air-gapped hosts pre-seed the HuggingFace cache.
- **Registration** (`config/openclaw.json`): `python3 -u mcp-servers/rag-mcp/rag_mcp_server.py`

## Tests

```bash
pytest tests/unit/test_rag_*.py tests/integration/test_rag_mcp.py   # offline mechanics suite
pytest tests/integration/test_rag_eval.py                            # golden-set eval (operator-supplied; skips without one)
```

## Mutation audit status

Mutation responses now include an `audit` object: `recorded` with a GAIT commit
reference, or `unavailable` with a warning. An unavailable audit does not undo a
completed data write; do not repeat the write solely to retry logging. These
components declare `gait-ai` in their own runtime and require an initialized
GAIT repository discoverable from the server working directory.
