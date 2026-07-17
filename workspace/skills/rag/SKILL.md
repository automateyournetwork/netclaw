# Skill: RAG Knowledge Base

**Purpose**: Give NetClaw a fully offline, user-curated document knowledge base — vendor guides, standards (RFC/IEEE/vendor), customer design documents, install guides — with agentic retrieval, mandatory citations, and opt-in point-in-time snapshots.

## Overview

Users teach NetClaw by uploading documents (Slack attachment, HUD Knowledge panel, or URL). Documents are parsed, chunked structure-aware, embedded locally, and stored at `~/.openclaw/rag/`. Retrieval is a tool NetClaw invokes on its own judgment — iteratively, with self-critique — never a fixed pipeline.

**This is NOT memory.** The knowledge base holds only what users deliberately put into it. NetClaw's own experience (facts, session summaries, decisions, entity graphs) lives in the Memory MCP (`memory_*` tools, `~/.openclaw/memory/`). Neither store writes into the other.

## MCP Tools

| Tool | WHEN to use |
|------|-------------|
| `rag_ingest` | A document file on disk should be learned |
| `rag_ingest_base64` | A Slack attachment should be learned (decode → ingest) |
| `rag_ingest_url` | The user asks to ingest a web page (ALWAYS preview scope first) |
| `rag_search` | Question concerns vendor procedures, customer standards, install steps, or ingested content |
| `rag_list` | User asks what the knowledge base contains |
| `rag_stats` | User asks about corpus size/health or retrieval telemetry |
| `rag_update_metadata` | Fix a document's doc_type/title/version |
| `rag_delete` | User asks to remove a document (CONFIRM with the user first) |
| `rag_reindex` | Chunking/embedding config changed (CONFIRM with the user first) |
| `rag_snapshot` | User EXPLICITLY asks to store live output for later comparison (confirm scope first — never automatic) |

## The Four Knowledge Sources (routing rules)

Route every question to the right source. Most questions need NO retrieval.

1. **Parametric knowledge** — timeless networking fundamentals (OSPF LSA types, BGP path selection). Answer directly. Do not search.
2. **Memory MCP** (`memory_recall`, `memory_get_facts`, `memory_get_decisions`) — NetClaw's own past sessions, learned facts, and decisions about THIS network. "What was that BGP issue last month?" goes here, never to `rag_search`.
3. **RAG knowledge base** (`rag_search`) — user-uploaded documents. Vendor procedures, customer standards, install steps. Check it BEFORE declaring ignorance on these topics.
4. **Live MCP servers** (pyATS, NetBox, etc.) — current network state. NEVER answer a live-state question from the RAG store. The only exception is an explicitly requested snapshot, whose age must always be shown.

When a question legitimately touches both Memory and the knowledge base, consult both — but attribute every part of the answer to its actual source. Memory recall is never presented as a document citation, and vice versa.

"Remember this document" → ingestion (RAG). "Remember that PE2 is in maintenance until Friday" → Memory (`memory_record_fact`).

## Workflow: Slack Document Upload

When a user posts a file attachment in the Slack channel and asks NetClaw to learn it:

1. Download the attachment content.
2. Call the ingest tool with the base64-encoded file:

   ```bash
   python3 $MCP_CALL "python3 -u $RAG_MCP_SCRIPT" rag_ingest_base64 \
     '{"filename": "wlc-9800-upgrade-guide.pdf", "content_base64": "<b64>", "doc_type": "vendor"}'
   ```

3. Infer `doc_type` from the user's words ("this is our customer standard" → `customer`); default `other`.
4. Confirm in-thread with what was learned: title, doc_type, page count, chunk count, collection — plus the `example_question` from the response, so the user learns what they can now ask.
5. If the response is `deduplicated: true`, say the document was already indexed. If `reindexed: true`, say the prior version was replaced.
6. Errors (unsupported format, size cap, parse failure) are reported verbatim — never silently swallowed.

Supported formats: PDF, Markdown, HTML, TXT, DOCX, XLSX, PPTX, VSDX natively; legacy DOC/XLS/PPT/VSD when LibreOffice is installed.

## Workflow: URL Ingestion (always preview first)

When a user asks to ingest a web page:

1. **Preview**: `rag_ingest_url {"url": "...", "mode": "preview"}` — returns the page title, the same-domain pages it links to (depth 1, capped at `RAG_CRAWL_MAX_PAGES`), and a `scope_token`. No ingestion happens.
2. **Confirm scope with the user**: "That page links to 6 same-domain pages. Ingest just the page, or all 7?" ALWAYS offer the single-page fallback. If the preview was truncated, say so.
3. **Ingest**:
   - Single page: `rag_ingest_url {"url": "...", "mode": "ingest"}`
   - Page + linked pages (only after explicit confirmation): `rag_ingest_url {"url": "...", "mode": "ingest", "include_linked": true, "scope_token": "<from preview>"}`
4. Confirm as with file ingestion. Each page records its own URL as source. PDFs served at URLs are handled automatically.

Never call `mode="ingest"` with `include_linked=true` without having shown the preview and obtained the user's confirmation — the server rejects a missing/stale `scope_token`.

## The Agentic Retrieval Protocol

Retrieval is a tool you wield, not a pipeline you sit inside. For every question:

### 1. Route first (Adaptive RAG)

Decide whether to retrieve AT ALL using the four-source rules above. Most questions need no retrieval:

| Question | Route | Why |
|----------|-------|-----|
| "What's the OSPF LSA type for external routes?" | Answer directly | Timeless fundamental |
| "What was that BGP issue last month on PE2?" | `memory_recall` | Your own past experience |
| "What does our customer standard require for change windows?" | `rag_search` (filter `doc_type: customer`) | User-uploaded document |
| "What's the current BGP state on PE2?" | Live MCP (pyATS) | Live network state — NEVER RAG |
| "Upgrade the lab WLC per our standards" | `rag_search` for procedure/standards, THEN live MCP for pre-checks | Mixed — each part to its source |

### 2. Rewrite and decompose

Rewrite conversational phrasing into retrieval-friendly queries ("how do I get the new code on the WLC" → "WLC software upgrade procedure install activate commit"). Decompose multi-part questions into independent sub-queries, retrieved separately with scoped filters, then synthesized. Give each sub-query a `sub_query_id` and pass `round` on every `rag_search` call so the budget is auditable.

### 3. Critique after every retrieval (Self-RAG)

Grade the returned chunks: do they actually answer the question?

- **Yes** → answer, citing every claim.
- **Partially / no** → rewrite the query (different terms, add filters) and re-retrieve.
- **`low_confidence: true` on results** → treat as signal, never as answer material.

### 4. Respect the iteration budget — 3 rounds per sub-query

Each sub-query gets at most 3 retrieval rounds (initial + 2 refinements; `RAG_MAX_ROUNDS`). **Stop condition**: when a sub-query's budget is exhausted, stop retrieving for it and state plainly what you found (cited) and what remains unanswered. Do not loop. Do not pad.

### 5. Honest miss

If the corpus doesn't cover the topic — empty results, `corpus_empty: true`, or only low-confidence chunks after refinement — say so:

> "The knowledge base doesn't cover Nexus 9300 upgrades. I can ingest a document if you have one — drop it in this channel."

NEVER answer from irrelevant or low-confidence chunks. NEVER present a guess as knowledge-base content. A fabricated answer is worse than an honest gap.

## Citation Rules (non-negotiable)

Every claim derived from retrieved content carries a citation:

```
[WLC 9800 Upgrade Guide §4.2, p.31 — ingested 2026-07-01]
```

Use the `citation` field returned by `rag_search` verbatim. A claim you cannot attribute to a specific retrieved chunk is NOT presented as coming from the knowledge base. Chunk IDs stay in the retrieval log — never show them to users.

When synthesizing across multiple documents, every combined claim must be supportable by at least one cited chunk. Do not blend unrelated chunks into a claim none of them supports — that is synthesis hallucination.

## Snapshots — the ONLY sanctioned RAG use of live data

`rag_snapshot` exists for one purpose: explicit point-in-time comparison ("snapshot the BGP tables so we can compare next month"). It is NEVER a substitute for a live MCP query.

**Absolute prohibition**: NEVER invoke `rag_snapshot` automatically, from a heartbeat, on a schedule, or as a side effect of another task. It runs only on an explicit human request, and only after you confirm scope.

Workflow:

1. User explicitly asks to snapshot live output.
2. **Confirm scope before executing** (HIIL gate): which devices, which commands, what label. "Scope: PE1, PE2 — `show ip bgp` via pyATS, into `snapshot_core-bgp_<timestamp>`. Confirm?"
3. Collect the output via the existing MCP tools (pyATS etc.).
4. Call `rag_snapshot {"label": "core-bgp", "content": "<output>", "source_description": "core router BGP tables", "devices": ["PE1","PE2"], "commands": ["show ip bgp"]}`.
5. Report what was stored **including the per-type redaction counts** from the response — secrets (passwords, SNMP communities, auth keys, pre-shared keys) are scrubbed before vectorization, and a zero count is reported explicitly.

When ANY answer later uses snapshot data:

- **Lead with the staleness notice**: "From snapshot core-bgp — captured 2026-07-16 14:02 UTC — 31 days ago (live state is available via MCP tools): …" Use the `age_human`/`staleness_notice` fields verbatim.
- Remind the user that live state is one MCP call away.
- Snapshots older than `RAG_SNAPSHOT_WARN_DAYS` (default 90) are flagged `stale` — surface the flag. They are never auto-deleted; offer deletion instead.

## Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `RAG_DATA_DIR` | `~/.openclaw/rag` | Persistent store (never `~/.openclaw/memory/`) |
| `RAG_EMBEDDING_MODEL` | `BAAI/bge-small-en-v1.5` | Local embedding model |
| `RAG_RERANKER_MODEL` | `cross-encoder/ms-marco-MiniLM-L-6-v2` | Local reranker |
| `RAG_RERANK_ENABLED` | `true` | Disable on low-resource hosts |
| `RAG_MAX_DOC_MB` / `RAG_MAX_DOC_PAGES` | `100` / `1000` | Per-document ingestion caps |
| `RAG_CRAWL_MAX_PAGES` | `30` | Depth-1 crawl preview bound |
| `RAG_SNAPSHOT_WARN_DAYS` | `90` | Snapshot staleness warning |
| `RAG_MAX_ROUNDS` | `3` | Retrieval rounds per sub-query |
| `RAG_MCP_SCRIPT` | — | Path to `rag-mcp/rag_mcp_server.py` for `$MCP_CALL` |

## Example Usage

```text
User: (attaches customer-wlan-standard.docx) learn this, it's our customer standard
NetClaw: Learned "Customer WLAN Standard" (customer, 24 pages, 61 chunks, documents).
         Try asking: "What does our standard 'Customer WLAN Standard' say about maintenance windows?"
```
