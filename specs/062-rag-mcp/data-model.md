# Data Model: Agentic RAG Knowledge Base (rag-mcp)

**Date**: 2026-07-16 | **Storage root**: `~/.openclaw/rag/` (never `~/.openclaw/memory/` — FR-030)

```text
~/.openclaw/rag/
├── rag.db          # SQLite registry (tables below)
├── chroma/         # ChromaDB PersistentClient (dense vectors)
├── bm25/           # <collection>.pkl keyword indexes
├── sources/        # retained originals, <document_id>/<original filename>
└── intake/         # transient upload landing zone (Slack base64 / HUD multipart)
```

## SQLite: `rag.db`

### `documents`

One row per ingested document **or** snapshot (discriminated by `kind`).

| Field | Type | Constraints / Notes |
|---|---|---|
| `id` | TEXT PK | `doc_<12-hex>` / `snap_<12-hex>` |
| `kind` | TEXT | `document` \| `snapshot` |
| `title` | TEXT NOT NULL | Parsed or user-supplied |
| `source` | TEXT NOT NULL | Filename, URL, or `slack:<channel>` (FR-006) |
| `doc_type` | TEXT | `vendor` \| `standard` \| `customer` \| `install-guide` \| `other` (default `other`, editable — FR-008) |
| `version` | TEXT NULL | User-supplied or parsed (FR-006) |
| `content_hash` | TEXT NOT NULL, UNIQUE per kind | SHA-256 of source bytes; drives dedupe/re-index (FR-007) |
| `collection` | TEXT NOT NULL | `documents` or `snapshot_<label>_<ISO8601>` (FR-015) |
| `ingest_ts` | TEXT NOT NULL | ISO-8601 UTC |
| `page_count` | INTEGER NULL | Where format provides pages |
| `chunk_count` | INTEGER NOT NULL DEFAULT 0 | Set when status → `ready` |
| `source_path` | TEXT NULL | Retained original under `sources/` (FR-052); NULL for snapshots |
| `ingest_status` | TEXT NOT NULL | State machine below; HUD progress source (FR-062) |
| `error` | TEXT NULL | Verbatim failure message when `status='error'` |
| `capture_ts` | TEXT NULL | Snapshots only: when the live data was captured (FR-073) |
| `capture_devices` | TEXT NULL | Snapshots only: JSON list of device/source identifiers |
| `capture_commands` | TEXT NULL | Snapshots only: JSON list of originating commands |
| `redaction_counts` | TEXT NULL | Snapshots only: JSON `{type: count}` incl. zeros (FR-072) |

**`ingest_status` state machine** (atomicity edge case): `pending → parsing → chunking → embedding → ready` | any → `error`. Only `ready` rows are searchable/listable as indexed. On server startup, rows stuck in a non-terminal state are swept to `error` ("interrupted — source retained, re-ingest to retry"); their partial Chroma/BM25 entries are purged. Chunks are committed to Chroma + BM25 *before* the row flips to `ready` (single SQLite transaction for the flip).

**Validation rules**: size cap enforced pre-`parsing` (reject > `RAG_MAX_DOC_MB` MB or > `RAG_MAX_DOC_PAGES` pages — FR-008a); identical `content_hash` + `kind='document'` → no-op "already indexed"; same `title` + different hash → re-index (delete old chunks, ingest new, user informed — FR-007).

### `retrieval_log` (FR-025)

| Field | Type | Notes |
|---|---|---|
| `id` | INTEGER PK AUTOINCREMENT | |
| `ts` | TEXT | ISO-8601 UTC |
| `query` | TEXT | As received |
| `collection` | TEXT | |
| `filters` | TEXT NULL | JSON |
| `k` | INTEGER | |
| `chunk_ids` | TEXT | JSON list returned (citation traceability — FR-044 log-only chunk IDs) |
| `scores` | TEXT | JSON list, parallel to `chunk_ids` |
| `latency_ms` | INTEGER | |
| `low_confidence` | INTEGER | Count of flagged results |
| `round` | INTEGER NULL | 1–3 within a sub-query (budget audit — FR-043) |
| `sub_query_id` | TEXT NULL | Groups rounds of one decomposed sub-query |

### `telemetry_rollup` (FR-083)

Rolling aggregates recomputed on write (or derived on read for v1): `query_count`, `mean_latency_ms`, `re_retrieval_rate` (share of sub-queries with round > 1), `low_confidence_rate`. Exposed via `rag_stats`.

### `schema_version`

Single row: `version INTEGER` (starts at 1) — migration marker (FR-054).

## ChromaDB: chunk records

Collections: `documents` + `snapshot_*`. Each chunk:

| Component | Content |
|---|---|
| `id` | `chunk_<doc_id>_<seq>` |
| embedded text | `"{breadcrumb}\n\n{chunk_text}"` (breadcrumb prefix per FR-012) |
| metadata | `document_id`, `title`, `doc_type`, `source`, `breadcrumb` (`Title > Chapter > Section`), `page` (INT, nullable), `section` (TEXT, nullable), `ingest_ts`, `atomic` (bool: unsplittable code/config/table block), `kind`; snapshots additionally `capture_ts`, `device`, `command` (FR-014, FR-073) |

Chunking invariants (FR-010/011): 400–800 tokens (embedder tokenizer), 10–15% overlap, heading-boundary-first splits, atomic blocks never split (oversized atomic block = its own chunk with `atomic=true`).

## BM25 pickles: `bm25/<collection>.pkl`

`{ "chunk_ids": [...], "tokenized_corpus": [[token,...],...], "built_ts": iso8601 }` — rebuilt whole on ingest/delete (corpus ≤ 5k chunks makes this cheap, FR-016). Tokenizer preserves networking tokens (`Gi0/0/1`, `192.0.2.0/24`, `CVE-…`) as single tokens.

## Derived / in-memory entities

- **SearchResult** (tool return shape): `chunk_text`, `score`, `chunk_id`, `title`, `doc_type`, `section`, `page`, `ingest_ts`, `low_confidence`; snapshots add `capture_ts`, `age_human` ("captured 2026-07-16 14:02 UTC — 31 days ago", FR-027).
- **CrawlPreview**: `url`, `title`, `linked_pages[] (same-domain, depth 1, capped at RAG_CRAWL_MAX_PAGES)`, `scope_token` — the token must be echoed by the ingest call, making the FR-004 confirmation gate structural.
- **GoldenSetEntry** (operator-supplied YAML): `question`, `expected_doc` (title or id), `answer_facts[]`, optional `doc_type_filter` — format shipped as `golden_set.example.yaml`, no fixture documents shipped (clarified).

## Relationships

```text
Document 1 ── * Chunk           (Chroma metadata document_id; cascade delete via rag_delete)
Document 1 ── 1 SourceFile      (sources/<doc_id>/…; basis for rag_reindex; absent for snapshots)
Collection 1 ── * Chunk         (Chroma collection + BM25 pickle pair)
RetrievalLog * ── * Chunk       (chunk_ids JSON — citation traceability)
Snapshot = Document(kind=snapshot) 1 ── 1 RedactionReport (redaction_counts JSON)
```

## Isolation invariant (GP-7 / FR-030 / SC-009)

No table, collection, pickle, or path above lives under `~/.openclaw/memory/`; rag-mcp opens no handle to `memory.db` or memory-mcp's Chroma directory. The only permitted overlap is the read-only HuggingFace model cache.
