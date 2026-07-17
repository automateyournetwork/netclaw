# Contract: rag-mcp MCP Tools

**Transport**: stdio (FastMCP, JSON-RPC lifecycle per Constitution V)
**Response envelope** (all tools, memory-mcp convention): `{"success": bool, "data": <payload>|null, "error": {"code": str, "message": str}|null}`
**Env**: `RAG_DATA_DIR` (default `~/.openclaw/rag`), `RAG_EMBEDDING_MODEL` (default `BAAI/bge-small-en-v1.5`), `RAG_RERANKER_MODEL` (default `cross-encoder/ms-marco-MiniLM-L-6-v2`), `RAG_RERANK_ENABLED` (default `true`), `RAG_RELEVANCE_FLOOR` (default `0.3`), `RAG_MAX_DOC_MB` (default `100`), `RAG_MAX_DOC_PAGES` (default `1000`), `RAG_CRAWL_MAX_PAGES` (default `30`), `RAG_SNAPSHOT_WARN_DAYS` (default `90`), `RAG_MAX_ROUNDS` (default `3`). No credentials (Constitution XIII).

Error codes: `UNSUPPORTED_FORMAT`, `SIZE_LIMIT_EXCEEDED`, `PARSE_FAILED`, `CONVERTER_UNAVAILABLE`, `ALREADY_INDEXED` (soft — returned as success with `deduplicated: true`), `NOT_FOUND`, `EMPTY_CORPUS` (soft), `SCOPE_TOKEN_INVALID`, `MODELS_NOT_CACHED`, `FETCH_FAILED`.

---

## 1. `rag_ingest`

Ingest a file already on local disk. Single pipeline entry used by all paths (FR-005).

**Params**: `file_path: str` (required) · `doc_type: str = "other"` (`vendor|standard|customer|install-guide|other`) · `title: str|null` · `version: str|null` · `source: str|null` (override, e.g. `slack:#netclaw`)

**Returns** (`data`): `document_id`, `title`, `doc_type`, `source`, `page_count`, `chunk_count`, `collection`, `ingest_ts`, `deduplicated: bool`, `reindexed: bool`, `example_question: str` (usage-teaching hook, FR-048)

**Behavior**: size cap pre-check (FR-008a) → parse (two-tier formats, FR-002) → chunk → embed → dual-index → registry flip to `ready` → GAIT commit (FR-009). Hash match ⇒ `deduplicated: true` no-op; same-title new hash ⇒ `reindexed: true` (FR-007). Original retained under `sources/` (FR-052).

## 2. `rag_ingest_base64`

Slack-attachment adapter (packet-analysis `save_pcap_from_base64` pattern, FR-003). Decodes into `intake/`, then delegates to the `rag_ingest` pipeline.

**Params**: `filename: str` · `content_base64: str` · plus `doc_type`/`title`/`version` as above (`source` defaults to `slack:attachment`)
**Returns**: same as `rag_ingest`.

## 3. `rag_ingest_url`

Two-phase URL ingestion with structural crawl-confirmation gate (FR-004).

**Params**: `url: str` · `mode: str = "preview"` (`preview|ingest`) · `include_linked: bool = false` · `scope_token: str|null` · `doc_type`/`title` as above

**`mode="preview"` returns**: `url`, `title`, `content_type`, `linked_pages: [{url, title?}]` (same-domain, depth 1, ≤ `RAG_CRAWL_MAX_PAGES`, truncation flagged), `scope_token`
**`mode="ingest"` returns**: list of per-page `rag_ingest` results. Requires the `scope_token` from a preceding preview when `include_linked=true` (else `SCOPE_TOKEN_INVALID`) — the agent must show the preview and get user confirmation between the two calls. Non-HTML content dispatches to the matching parser.

## 4. `rag_search`

Hybrid retrieve → RRF → rerank → top-k (FR-020–027). The agent's retrieval tool (GP-3).

**Params**: `query: str` · `k: int = 5` · `collection: str = "documents"` (or a `snapshot_*` name; explicit multi-collection = repeated calls, FR-015) · `filters: dict|null` (`doc_type`, `document_id`, `title`, `ingested_after`, `ingested_before` — FR-023) · `round: int|null` · `sub_query_id: str|null` (budget-audit logging, FR-043)

**Returns** (`data`): `results: [{chunk_text, score, chunk_id, title, doc_type, section, page, ingest_ts, low_confidence, citation}]` · `corpus_empty: bool` · `collection` · `latency_ms`. `citation` is the preformatted user-visible string `[Title §sec, p.N — ingested YYYY-MM-DD]` (chunk IDs log-only per clarification). Snapshot results add `capture_ts`, `age_human` — verbatim-surfacing required (FR-027/046). Sub-floor results flagged, never dropped (FR-024). Every call logged to `retrieval_log` (FR-025). p50 < 2 s at ≤ 5k chunks (FR-026).

## 5. `rag_list`

**Params**: `kind: str = "all"` (`documents|snapshots|all`)
**Returns**: `documents: [full metadata per data-model]` · `snapshots: [metadata + capture_ts + age_human + stale: bool (> RAG_SNAPSHOT_WARN_DAYS)]` — separate arrays (FR-050, FR-074).

## 6. `rag_delete`

**Params**: `document_id: str` · `confirmed: bool = false`
**Returns**: `deleted: bool`, `chunks_removed: int`
**Behavior**: `confirmed=false` ⇒ returns a confirmation-required notice (HIIL gate, FR-053; SKILL.md instructs the agent to obtain user confirmation first). Removes chunks from Chroma **and** BM25, deletes retained source, GAIT-commits (FR-051). Works for snapshots too (FR-074).

## 7. `rag_reindex`

**Params**: `document_id: str` · `confirmed: bool = false`
**Returns**: same shape as `rag_ingest` result
**Behavior**: re-parse/re-chunk/re-embed from retained original under current config (FR-052); HIIL-gated like delete (FR-053); `NOT_FOUND` if source file missing (snapshots are not reindexable — no retained source).

## 8. `rag_update_metadata`

**Params**: `document_id: str` · `doc_type: str|null` · `title: str|null` · `version: str|null`
**Returns**: updated document metadata (FR-008). Updates registry + chunk metadata in Chroma.

## 9. `rag_snapshot`

Opt-in vectorization of live output (FR-070–075). **Never invoked automatically** — SKILL.md prohibition + conversational HIIL confirmation of scope before calling (FR-071).

**Params**: `label: str` (slug) · `content: str` (raw/parsed show-command output or JSON) · `source_description: str` · `devices: [str]` · `commands: [str]` · `capture_ts: str|null` (default now, ISO-8601 UTC)
**Returns**: `collection` (`snapshot_<label>_<ISO8601>`), `snapshot_id`, `chunk_count`, `redaction_counts: {type: count}` (zeros included, FR-072), `capture_ts`
**Behavior**: scrub → chunk (device/command-aware) → embed into the NEW snapshot collection (never `documents`, FR-070) → GAIT commit.

## 10. `rag_stats`

**Returns**: `document_count`, `snapshot_count`, `total_chunks`, `disk_usage_bytes`, `embedding_model`, `reranker_model`, `rerank_enabled`, `collections: [names]`, `telemetry: {query_count, mean_latency_ms, re_retrieval_rate, low_confidence_rate}` (FR-050, FR-083).

---

**Tool count**: 10 (the 9 named in FR-047 — with ingestion split into `rag_ingest` + `rag_ingest_base64` adapters — plus `rag_ingest_url`). TOOLS.md WHEN-guidance one-liners required for each (FR-047).
