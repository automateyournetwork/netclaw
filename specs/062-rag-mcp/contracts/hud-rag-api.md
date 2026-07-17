# Contract: HUD Knowledge Panel — Express API + WebSocket Events

**Server**: `ui/netclaw-visual/server.js` (existing Express + `ws` at `/ws`)
**Panel**: `src/panels/KnowledgePanel.js` (TwitterPanel class convention: constructed with shared socket; `render()` / `getTemplate()` / `setupEventListeners()`)
**Data access**: ALL endpoints (reads and mutations) invoke rag-mcp tools via the existing MCP-call child-process helper — uniform access path, no native Node SQLite dependency. No hardcoded data (FR-060).

## REST endpoints

### `GET /api/rag/documents`
Returns `{documents: [...], snapshots: [...]}` mirroring `rag_list` fields (title, doc_type, source, page_count, chunk_count, ingest_ts, ingest_status, error; snapshots add capture_ts, age_human, stale). Backing: `rag_list` via MCP-call helper.

### `GET /api/rag/stats`
Returns the `rag_stats` payload shape (corpus totals + telemetry) for the panel header (FR-083).

### `POST /api/rag/upload`
`multipart/form-data`: `file` (required), `doc_type`, `title` (optional). Server saves to `~/.openclaw/rag/intake/`, invokes `rag_ingest`, responds `202 {document_id, status: "pending"}` immediately; progress flows over WS. Errors: `413` over size cap (mirrors FR-008a with limit + override path in body), `415` unsupported format, `500` with verbatim ingest error (FR-062).

### `DELETE /api/rag/documents/:id`
Body `{confirm: true}` required (panel confirm dialog, FR-061) → invokes `rag_delete(confirmed=true)`. `400` without confirm; `404` unknown id.

### `POST /api/rag/documents/:id/reindex`
Body `{confirm: true}` required → invokes `rag_reindex(confirmed=true)`. Same error semantics.

## WebSocket events (via existing `broadcastWS(type, payload)`)

| type | payload | when |
|---|---|---|
| `rag_progress` | `{document_id, title, status}` — status ∈ `parsing, chunking, embedding, ready, error` (+ `error` text verbatim) | Server polls `documents.ingest_status` on its existing interval while any row is non-terminal (FR-062) |
| `rag_update` | `{documents_changed: true}` | Any registry change (ingest complete, delete, reindex, metadata edit) — panel re-fetches `GET /api/rag/documents` |

## Panel requirements (FR-060–063)

- Upload area: drag-and-drop + file picker; client-side size pre-check against the configured cap with clear message.
- Documents table: title, doc_type, source, pages, chunks, ingest date; per-row Delete / Re-index actions behind confirm dialogs.
- Progress: per-document live state chips driven by `rag_progress` (parsing → chunking → embedding → done); errors rendered verbatim.
- Snapshots: visually distinct section, capture timestamp + age badge, stale flag at > 90 days (FR-063, FR-074).
- New Node dependency: `multer` (multipart parsing) — the only addition to `ui/netclaw-visual/package.json`.
