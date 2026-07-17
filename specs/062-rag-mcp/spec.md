# Feature Specification: Agentic RAG Knowledge Base (rag-mcp)

**Feature Branch**: `062-rag-mcp`
**Created**: 2026-07-16
**Status**: Draft
**Input**: User description: "Agentic RAG Knowledge Base (rag-mcp): a fully offline, free, local document knowledge base for NetClaw with agentic retrieval, multi-format ingestion via Slack/HUD/URL, opt-in secret-scrubbed snapshots of live network output, HUD Knowledge panel, and an offline evaluation harness. Strictly separated from the existing Memory MCP (agent experience) — this store holds things USERS upload — with SOUL/MEMORY/SKILLS reworked so NetClaw knows it has a knowledge base to check."

## Overview

NetClaw gains a fully **offline, free, local** document knowledge base. Users augment NetClaw's knowledge by uploading documentation — install guides, standards (RFC/IEEE/vendor), vendor configuration guides, customer design documents — via Slack attachment, a new HUD upload panel, or by asking NetClaw to ingest a URL. Documents are parsed, chunked, embedded with local models, and stored persistently under `~/.openclaw/rag/`.

Retrieval is **agentic, not pipelined**: NetClaw treats retrieval as a tool call (`rag_search`) that it invokes on its own initiative, iteratively, with self-critique — the ReAct / Self-RAG pattern — rather than a one-shot pre-generation lookup. A new `rag` SKILL.md plus SOUL.md/TOOLS.md updates teach NetClaw HOW to ingest and WHEN (and when NOT) to retrieve.

The knowledge base is **not memory**. NetClaw already has a Memory MCP (`~/.openclaw/memory/`) holding its own experience: facts, session summaries, decisions, and entity relationships. The RAG store holds only what users deliberately put into it. The two systems share nothing but the concept of embeddings, and NetClaw's guidance documents are reworked so it always knows which of its four knowledge sources to consult: what it knows (parametric), what it has experienced (Memory), what it has been given (RAG knowledge base), and what is true right now (live MCP).

A separate, explicitly opt-in `rag_snapshot` tool vectorizes selected live network outputs into a timestamped collection — never automatically — with staleness always visible.

## Clarifications

### Session 2026-07-16

- Q: How does the 3-round retrieval budget (FR-043) interact with sub-query decomposition (FR-042)? → A: 3 rounds per sub-query — each decomposed sub-question gets its own initial + 2 refinements; the budget bounds refinement loops, not question complexity.
- Q: Must the chunk ID appear in the user-visible citation, or only in the retrieval log? → A: Log-only — visible citations stay human-readable (title, section/page, ingest date); chunk IDs are recorded in the retrieval log/GAIT for traceability.
- Q: What should the golden-set fixture documents be? → A: Do not ship fixture documents in the repo — the user will collect real documents later. Ship the harness and the golden-set file format; the evaluation gate runs only when a user-supplied golden set is present.
- Q: How should the installer treat rag-mcp? → A: Default-on component — installed and registered by default (skippable via the modular installer), embedding/reranker models downloaded at install time; the legacy-format conversion fallback is offered separately.
- Q: What per-document size limit should ingestion enforce? → A: Soft cap of 100 MB / 1,000 pages per document, configurable, enforced at all three entry points with a clear rejection message.

## Governing Principles

These principles are architectural boundaries, not suggestions. Every functional requirement below must be consistent with them.

- **GP-1 — RAG for knowledge, MCP for state.** Documents (slow-changing knowledge) live in the RAG store. Live network state comes from MCP servers (pyATS, NetBox, etc.) at question time. NetClaw MUST NEVER answer a question about current network state from the RAG store, with one exception: an explicitly requested, timestamped snapshot (see FR-070 – FR-075), whose age is always displayed.
- **GP-2 — Fully offline and free.** No cloud embedding APIs, no paid rerankers, no external vector DB services. Local embedding models, local vector store, local cross-encoder reranker only. The system must work air-gapped after initial model download.
- **GP-3 — Retrieval is a tool, not a pipeline.** `rag_search` is one tool among NetClaw's many. The agent decides whether to call it, how to phrase queries, whether results are good enough, and whether to re-retrieve — bounded by an explicit iteration budget (Adaptive RAG + Self-RAG/CRAG patterns).
- **GP-4 — Every retrieved claim is cited.** Any statement NetClaw makes that derives from retrieved content MUST carry a citation (document title, section, page where available, ingest date — with the underlying chunk ID traceable in the retrieval log). A claim it cannot cite, it does not make from RAG. This is the primary defense against synthesis hallucination.
- **GP-5 — Opt-in only for live data.** `rag_snapshot` is never called automatically, never in a heartbeat, never as a side effect. Explicit human request only, and confirmation is required before vectorizing.
- **GP-6 — Users own the corpus.** Every document is listable, inspectable, deletable, and re-indexable. Nothing is a black box.
- **GP-7 — Knowledge base is not memory.** The RAG store holds only user-supplied content (uploaded documents and explicitly requested snapshots). NetClaw's own experience — facts, session summaries, decisions, entity graphs — stays in the existing Memory MCP. The two systems are physically separate stores with separate tools, and NetClaw's guidance documents define which to consult for which question. Neither system ever writes into the other.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ingest a document via Slack and get cited answers (Priority: P1)

A user drags a vendor upgrade-guide PDF into the NetClaw Slack channel and says "learn this." NetClaw ingests it (reusing the packet-analysis attachment pattern), replies with title, doc type, page count, chunk count, and collection, and commits the ingestion decision to GAIT. In the same session, the user asks a question answered by that document and receives a correctly cited answer sourced from it.

**Why this priority**: This is the core value loop — a document goes in, cited knowledge comes out. Without it the feature does not exist. Slack is the primary NetClaw interaction surface today.

**Independent Test**: Upload a sample PDF via Slack, verify the ingestion confirmation message (title, doc type, pages, chunks, collection), then ask a question whose answer lives only in that PDF and verify the answer carries a citation in the required format.

**Acceptance Scenarios**:

1. **Given** an empty knowledge base, **When** a user posts a PDF attachment in the NetClaw Slack channel and says "learn this", **Then** NetClaw ingests it and replies in-thread with title, doc type, page count, chunk count, and collection name, and a GAIT commit records the ingestion decision.
2. **Given** a document ingested in this session, **When** the user asks a question answered by that document, **Then** NetClaw's answer includes at least one citation of the form `[Document Title §section, p.N — ingested YYYY-MM-DD]` traceable to a real chunk.
3. **Given** a previously ingested file, **When** the same file (identical content hash) is posted again, **Then** NetClaw responds "already indexed" and performs no duplicate ingestion.
4. **Given** a previously ingested title whose new upload has a different content hash, **When** it is posted, **Then** NetClaw re-indexes (old chunks removed, new chunks ingested) and informs the user it replaced the prior version.

---

### User Story 2 - Agentic retrieval with self-critique (Priority: P1)

A user asks "upgrade the lab WLC following our customer standards." NetClaw, unprompted, decomposes the question into sub-queries, searches the knowledge base against both the vendor guide and the customer standards document (scoped by metadata filters), critiques the results, re-retrieves once with a refined query, and answers with inline citations — then uses MCP tools for live pre-checks per GP-1.

**Why this priority**: Agentic behavior (decide-retrieve-critique-refine) is the differentiator over a dumb lookup pipeline; without it the knowledge base returns noise or hallucinations and destroys trust.

**Independent Test**: With two documents ingested (a vendor guide and a customer standard), ask a multi-part question requiring both. Verify via the retrieval log that multiple scoped sub-queries were issued, that the final answer cites both documents, and that any live-state portion of the answer came from MCP tools, not RAG.

**Acceptance Scenarios**:

1. **Given** a corpus with a vendor guide and a customer standards doc, **When** the user asks a multi-part procedural question spanning both, **Then** the retrieval log shows decomposed sub-queries with metadata filters and the answer cites chunks from both documents.
2. **Given** a first retrieval round returning weak results, **When** NetClaw grades them as insufficient, **Then** it rewrites the query and re-retrieves, staying within the hard cap of 3 rounds per sub-query.
3. **Given** the 3-round budget is exhausted without a full answer, **When** NetClaw responds, **Then** it states what it found (cited) and what remains unanswered — it does not fabricate.
4. **Given** a question that mixes document knowledge with current network state, **When** NetClaw answers, **Then** the live-state portion is sourced from MCP tools and no live-state claim is answered from the RAG store.

---

### User Story 3 - Honest miss on uncovered topics (Priority: P2)

A user asks about a platform with no documents in the corpus. NetClaw retrieves, grades the chunks as irrelevant, and says the knowledge base does not cover it — offering to ingest a relevant document — instead of fabricating an answer.

**Why this priority**: Trust hinges on honest misses. A knowledge base that fabricates on gaps is worse than none.

**Independent Test**: Ask a question about a product family absent from the corpus; verify NetClaw explicitly reports the gap, offers ingestion, and the retrieval log shows the low-relevance grading.

**Acceptance Scenarios**:

1. **Given** a corpus with no content about platform X, **When** the user asks a platform-X-specific procedural question, **Then** NetClaw reports the knowledge base does not cover it and offers to ingest a document, within the 3-round budget.
2. **Given** retrieval results below the relevance floor, **When** NetClaw composes its answer, **Then** it never presents low-confidence chunks as authoritative answers.

---

### User Story 4 - Route each question to the right knowledge source (Priority: P2)

A user asks "what's the OSPF LSA type for external routes?" NetClaw answers from its own knowledge without searching the knowledge base — simple, timeless facts don't pay the retrieval tax. A question about current network state routes to MCP tools. A question about a past troubleshooting session ("what was that BGP issue last month?") routes to the Memory MCP, not the knowledge base. A question about an uploaded standard routes to the knowledge base, not memory.

**Why this priority**: Adaptive routing keeps the system fast and prevents cross-contamination between the four knowledge sources; it is the enforcement of GP-1, GP-3, and GP-7.

**Independent Test**: Ask four questions — a fundamentals question, a live-state question, a past-session question, and an uploaded-document question — and verify via GAIT/retrieval logs that each used only its correct source (none, MCP, Memory, RAG respectively).

**Acceptance Scenarios**:

1. **Given** any corpus state, **When** the user asks a timeless networking-fundamentals question, **Then** NetClaw answers without calling `rag_search` (verified in the retrieval log).
2. **Given** any corpus state, **When** the user asks about current network state, **Then** NetClaw uses MCP tools and does not consult the RAG store.
3. **Given** past sessions stored in the Memory MCP, **When** the user asks about a previous troubleshooting session or decision, **Then** NetClaw uses memory tools (`memory_recall`, `memory_get_decisions`) and does not search the RAG knowledge base for it.
4. **Given** an uploaded customer standard, **When** the user asks what the standard requires, **Then** NetClaw searches the RAG knowledge base and does not present agent memory as document content.

---

### User Story 5 - Ingest from a URL (Priority: P2)

A user says "ingest https://vendor.example/wlc-9800-upgrade-guide". NetClaw fetches the page, confirms crawl scope (the page plus same-domain pages linked from it, one level deep), converts content to text preserving heading structure, ingests it with the URL recorded as source, and confirms as in User Story 1.

**Why this priority**: Much vendor documentation lives on the web; URL ingestion removes the download-then-upload step. It builds on the P1 ingestion path.

**Independent Test**: Ask NetClaw to ingest a known documentation URL; verify the scope confirmation, the ingested document's metadata (URL as source), and a cited answer from its content.

**Acceptance Scenarios**:

1. **Given** a user-supplied URL, **When** NetClaw prepares to ingest, **Then** it first reports how many same-domain linked pages (depth 1) are in scope and asks for confirmation before fetching beyond the target page.
2. **Given** confirmation of single-page scope only, **When** ingestion completes, **Then** only the target page is indexed, with the URL recorded as its source.
3. **Given** confirmation of depth-1 scope, **When** ingestion completes, **Then** the target page and its same-domain linked pages are indexed, each recording its own URL as source.

---

### User Story 6 - HUD Knowledge panel: upload, browse, manage (Priority: P3)

A user opens the HUD's new **Knowledge** panel, uploads a customer standards document by drag-and-drop, watches ingestion progress (parsing → chunking → embedding → done), and sees it appear in the indexed-documents view with metadata, chunk count, and per-document delete / re-index actions. Snapshot collections render in a visually distinct section with age badges.

**Why this priority**: The HUD gives corpus visibility and management (GP-6) but the knowledge base is fully usable via Slack and conversation without it.

**Independent Test**: Upload a document via the HUD panel, watch the progress states, verify the table row matches `rag_list` output, then delete it via the row action (with confirmation) and verify it disappears from both the table and search results.

**Acceptance Scenarios**:

1. **Given** the HUD Knowledge panel is open, **When** a user drags a supported file onto the upload area, **Then** ingestion progress states are shown live and the document appears in the table with title, doc type, source, pages, chunks, and ingest date — no hardcoded data.
2. **Given** an indexed document row, **When** the user clicks delete and confirms, **Then** the document's chunks are removed from all indexes and the deletion is recorded in GAIT.
3. **Given** an ingestion failure, **When** it occurs, **Then** the error is surfaced verbatim in the panel.
4. **Given** at least one snapshot collection exists, **When** the panel renders, **Then** snapshots appear in a visually distinct section with capture timestamp and an age badge.

---

### User Story 7 - Opt-in snapshot of live network output (Priority: P3)

A user says "snapshot the BGP tables of the core routers into RAG so we can compare next month." NetClaw confirms scope, runs the show commands via existing MCPs, scrubs secrets, vectorizes the output into a timestamped snapshot collection, and reports what was stored, including redaction counts. A month later, retrieval from that snapshot always displays its capture timestamp and age, and reminds the user that live state is available via MCP.

**Why this priority**: Point-in-time comparison is valuable but strictly bounded by GP-1/GP-5; it must never become an accidental substitute for live queries, so it ships after the core knowledge loop is proven.

**Independent Test**: Request a snapshot, verify the confirmation gate, redaction count in the completion message, and — on a later retrieval — the verbatim staleness string and live-state reminder.

**Acceptance Scenarios**:

1. **Given** a user requests a snapshot, **When** NetClaw prepares it, **Then** it confirms scope with the user before vectorizing, and never initiates a snapshot automatically, from a heartbeat, or as a side effect.
2. **Given** snapshot content containing credentials (password hashes, SNMP communities, auth keys, pre-shared keys), **When** it is vectorized, **Then** each secret is replaced with a typed redaction placeholder and the confirmation message reports the redaction count by type.
3. **Given** a stored snapshot, **When** any answer uses its content, **Then** the answer leads with a human-readable staleness statement ("captured 2026-07-16 14:02 UTC — 31 days ago") and reminds the user live state is available via MCP.
4. **Given** a snapshot older than the retention warning threshold (default 90 days), **When** it is listed or retrieved from, **Then** it is flagged as stale; it is never auto-deleted.

---

### Edge Cases

- **Duplicate content, different filename**: content hash matches an existing document → "already indexed" no-op (FR-007), regardless of filename.
- **Same title, changed content**: hash differs → re-index with user notification (FR-007).
- **Unsupported file type**: ingestion rejects with a clear message listing supported formats; nothing is partially indexed.
- **Oversized document**: a file exceeding the configured cap (default 100 MB / 1,000 pages) is rejected at intake with the limit and override path stated; nothing is partially indexed.
- **Legacy binary format with conversion backend unavailable**: if the local office-document conversion fallback is not installed, ingestion of legacy formats (DOC/XLS/PPT/VSD) fails gracefully with an actionable message; modern formats remain unaffected.
- **Corrupt or image-only (scanned) PDF**: parse failure or zero extractable text → ingestion error surfaced verbatim (no silent empty document); OCR is out of scope for v1.
- **Oversized atomic block**: a code/config block or table larger than the chunk target becomes its own chunk, never split (FR-011).
- **URL crawl scope explosion**: depth-1 page count exceeds a sane bound → NetClaw reports the count and requires explicit confirmation, offering single-page fallback.
- **Unreachable or non-HTML URL**: fetch errors reported verbatim; PDFs served at URLs are ingested via the PDF path.
- **Search on empty corpus**: `rag_search` returns an empty result set with a clear "corpus is empty" signal — never an error crash — and the agent reports the gap honestly.
- **First run before models are cached**: embedding/reranker models download once at install; a query attempted before models exist yields an actionable error, not a hang. Air-gapped hosts must pre-seed the model cache.
- **Reranker disabled (low-resource host)**: hybrid fusion results returned directly; result quality flag unchanged, evaluation harness documents the expected hit-rate delta.
- **Concurrent ingestions**: two simultaneous uploads must both complete without corrupting either index (serialized ingestion is acceptable).
- **Restart mid-ingestion**: a partially ingested document must not remain half-indexed; ingestion is atomic per document (all chunks committed or none, with the source file retained for retry).
- **Snapshot with zero secrets found**: confirmation still reports "0 redactions" so absence of scrubbing is distinguishable from scrubber failure.
- **Deletion of a document mid-conversation**: subsequent citations to deleted chunks must fail gracefully (chunk lookup miss reported, not fabricated content).
- **Ambiguous source question** ("what do we know about PE2 upgrades?"): may legitimately touch both Memory (past sessions) and the knowledge base (vendor guide); NetClaw may consult both but must attribute each part of the answer to its source — memory recall is never presented as a document citation, and vice versa.
- **User asks NetClaw to "remember" document content**: routes to ingestion (RAG), not to `memory_record_fact`; asking it to remember an operational fact ("PE2 is in maintenance until Friday") routes to Memory, not RAG.

## Requirements *(mandatory)*

### Functional Requirements

#### Ingestion (FR-001 – FR-009)

- **FR-001**: The knowledge base MUST be a standalone MCP server (`rag-mcp`), installed and registered **by default** by the NetClaw modular installer (skippable as a component, like other default-on components), with embedding/reranker models downloaded at install time and persistent storage at `~/.openclaw/rag/` that survives restarts and upgrades. The legacy-format conversion fallback (FR-002) is offered as a separate optional install step.
- **FR-002**: Ingestion MUST accept PDF, Markdown, HTML, and plain text natively, plus modern office formats (DOCX, XLSX, PPTX, VSDX) via direct local parsing, and legacy office formats (DOC, XLS, PPT, VSD) via a local, free, offline document-conversion fallback. Parsing MUST extract text, headings, tables, and page numbers where the format provides them. If the conversion fallback is unavailable, legacy-format ingestion MUST fail gracefully with an actionable message while all other formats continue to work.
- **FR-003**: Slack attachment ingestion MUST reuse the packet-analysis attachment pattern: file posted to the channel → downloaded → handed to `rag_ingest` → confirmation message in-thread.
- **FR-004**: `rag_ingest_url` MUST fetch a user-supplied URL and, on confirmation, same-domain pages linked from it to a maximum depth of 1. Before fetching beyond the target page, NetClaw MUST report the in-scope page count and obtain user confirmation (with a single-page-only fallback always offered). Content MUST be converted to text preserving heading structure, with each page's URL recorded as its source.
- **FR-005**: The HUD Knowledge panel MUST support drag-and-drop / file-picker upload routed to the same `rag_ingest` path (single ingestion code path for all three entry points: Slack, HUD, URL).
- **FR-006**: Every document MUST store metadata: title, source (filename/URL/Slack), doc_type (`vendor` | `standard` | `customer` | `install-guide` | `other`), version (user-supplied or parsed, optional), content hash, ingest timestamp, page count, chunk count, collection name.
- **FR-007**: Re-ingesting a file whose content hash matches an existing document MUST be a no-op with an "already indexed" response; a changed hash for the same title MUST trigger re-index (delete old chunks, ingest new) with the user informed.
- **FR-008**: Ingestion MUST infer doc_type from a user hint when given ("this is our customer standard") and default to `other` otherwise; doc_type MUST be editable via `rag_update_metadata`.
- **FR-008a (Size limit)**: Ingestion MUST enforce a configurable per-document soft cap (default 100 MB or 1,000 pages, whichever is hit first) at all three entry points, rejecting oversized documents with a clear message that states the limit and how to raise it.
- **FR-009**: Every ingestion, deletion, and re-index MUST be committed to GAIT describing what was ingested and why (GAIT records the AI's decisions, not just outcomes).

#### Chunking & Embedding (FR-010 – FR-016)

- **FR-010**: Chunking MUST be **structure-aware**, splitting on heading boundaries first, then paragraphs, targeting ~400–800 tokens with ~10–15% overlap. Fixed-size character splitting is prohibited as the primary strategy.
- **FR-011**: Chunking MUST NOT split atomic blocks: fenced code blocks, CLI/config blocks, and tables are kept whole (oversized atomic blocks become their own chunk).
- **FR-012**: Each chunk MUST be prefixed, before embedding, with a heading breadcrumb (`Document Title > Chapter > Section`) — an offline approximation of contextual retrieval that anchors chunks to their document context.
- **FR-013**: Embeddings MUST use a local embedding model (default: a small English model favoring CPU speed; a larger model documented as a configuration upgrade), downloaded once and cached; no network calls at query time.
- **FR-014**: Each chunk MUST store: chunk ID, parent document ID, breadcrumb, page/section reference, and all parent-document metadata needed for filtering and citation.
- **FR-015**: Document knowledge MUST live in a `documents` collection; snapshots live in separate `snapshot_<label>_<ISO8601>` collections (see FR-070). Collections are never mixed in a single search unless the agent explicitly requests both.
- **FR-016**: A keyword index MUST be maintained per collection alongside the dense index, persisted under `~/.openclaw/rag/`, and rebuilt on ingest/delete.

#### Separation from Memory (FR-030 – FR-033)

- **FR-030 (Storage isolation)**: `rag-mcp` MUST store all data under `~/.openclaw/rag/` and MUST NOT read from or write to the Memory MCP's store (`~/.openclaw/memory/`), MemPalace's store, or any other agent-memory system. The Memory MCP is not modified by this feature. The two systems MUST NOT share vector collections, databases, or indexes (a shared read-only model cache is permitted).
- **FR-031 (Content boundary)**: The RAG store MUST contain only user-supplied content: uploaded/URL-ingested documents and explicitly requested snapshots. NetClaw MUST NOT use `rag_ingest` or `rag_snapshot` to store its own session summaries, learned facts, decisions, or entity relationships — those continue to go to the Memory MCP. Conversely, memory tools MUST NOT be used to store document content ("remember this PDF" routes to ingestion, not `memory_record_fact`).
- **FR-032 (Source routing)**: NetClaw's guidance documents (SOUL.md and the `rag` + `memory` SKILL.md files) MUST define a four-source knowledge hierarchy with routing rules: (1) parametric knowledge for timeless fundamentals, (2) Memory MCP for NetClaw's own past sessions, facts, and decisions about THIS network, (3) the RAG knowledge base for user-uploaded documents and standards, (4) live MCP servers for current network state. Questions about past sessions/decisions route to memory tools; questions about documentation route to `rag_search`; both may be consulted for a complex task, but each part of the answer MUST be attributed to its actual source (memory recall is never presented as a document citation, and vice versa).
- **FR-033 (Knowledge-base awareness)**: SOUL.md MUST make NetClaw affirmatively aware that it has a user-curated knowledge base to check: when a question concerns vendor procedures, customer standards, or install steps, NetClaw's default behavior is to check the knowledge base (via `rag_search`, informed by corpus awareness from `rag_list`/`rag_stats`) before declaring ignorance or answering from general knowledge alone. The existing `memory` SKILL.md MUST gain a disambiguation note pointing document-content questions to the `rag` skill.

#### Retrieval — `rag_search` (FR-020 – FR-027)

- **FR-020**: `rag_search(query, k=5, collection="documents", filters=None)` MUST return top-k chunks with: chunk text, score, chunk ID, document title, doc_type, section/page, ingest timestamp, and (for snapshots) capture timestamp + computed age.
- **FR-021**: Retrieval MUST be **hybrid**: a dense (semantic) leg and a keyword leg each retrieve a candidate set; results are fused by reciprocal rank fusion. Exact-match tokens critical in networking — CLI syntax, CVE IDs, RFC numbers, interface names — MUST be findable even when semantic similarity misses them.
- **FR-022**: A **local cross-encoder reranker** (CPU-capable, configurable) MUST rerank the fused candidates down to the returned top-k. Reranking MUST be disableable via configuration for low-resource hosts.
- **FR-023**: `rag_search` MUST accept metadata filters (doc_type, document ID/title, ingest-date range) so the agent can scope retrieval (e.g., customer standards only).
- **FR-024**: Results below a configurable relevance floor MUST be returned flagged `low_confidence: true` rather than silently dropped, so the agent's critique step (FR-041) has signal.
- **FR-025**: Every `rag_search` call MUST be logged (query, collection, filters, chunk IDs returned, scores, latency) to a local retrieval log and summarized in GAIT when part of an operator-visible task.
- **FR-026**: `rag_search` median latency MUST be under 2 seconds on the reference host (CPU-only acceptable) for a corpus of ≤ 5,000 chunks.
- **FR-027**: Snapshot-collection results MUST always include a human-readable staleness string ("captured 2026-07-16 14:02 UTC — 31 days ago") that the agent is required to surface verbatim (see FR-046).

#### Agentic Behavior — SKILL.md / SOUL.md / TOOLS.md (FR-040 – FR-048)

- **FR-040 (Adaptive routing)**: The `rag` SKILL.md MUST give NetClaw explicit WHEN-to-retrieve criteria: retrieve for vendor-specific procedures, customer standards, install steps, ingested-document content; do NOT retrieve for timeless networking fundamentals it already knows; NEVER retrieve for live network state (route to MCPs per GP-1); route past-session/decision questions to Memory tools per GP-7. Most queries should skip retrieval entirely.
- **FR-041 (Self-critique)**: After every retrieval, NetClaw MUST grade the chunks: do they actually answer the question? If not, it either rewrites the query and re-retrieves, or reports honestly that the knowledge base doesn't cover it — never answers from irrelevant chunks.
- **FR-042 (Query rewriting & decomposition)**: SKILL.md MUST teach NetClaw to rewrite conversational questions into retrieval-friendly queries and to decompose multi-part questions into independent sub-queries retrieved separately, then synthesized.
- **FR-043 (Iteration budget)**: A hard cap of **3 retrieval rounds per sub-query** (initial + 2 refinements). When a question is decomposed (FR-042), each sub-query carries its own 3-round budget; an undecomposed question is a single sub-query. On exhaustion of any sub-query's budget, NetClaw states what it found and what remains unanswered for that part. The cap is configurable but MUST exist and MUST be documented in SKILL.md as a stop condition.
- **FR-044 (Citation grounding)**: Every claim derived from retrieved content MUST carry a user-visible citation of document title, section/page, and ingest date — format: `[WLC 9800 Upgrade Guide §4.2, p.31 — ingested 2026-07-01]` — and MUST be traceable to a specific chunk ID via the retrieval log (chunk IDs are log-only, never shown inline). Claims NetClaw cannot attribute to a specific chunk MUST NOT be presented as coming from the knowledge base.
- **FR-045 (Synthesis discipline)**: When combining chunks from multiple documents, each combined claim MUST be supportable by at least one cited chunk; SKILL.md MUST explicitly warn against blending unrelated chunks into unsupported claims (synthesis hallucination).
- **FR-046 (Staleness surfacing)**: Any answer using snapshot data MUST lead with the snapshot's capture time and age, and remind the user live state is available via MCP.
- **FR-047**: SOUL.md MUST be updated with GP-1 and GP-7 as core beliefs (including the four-source knowledge hierarchy per FR-032/FR-033); TOOLS.md MUST be updated with `rag_search`, `rag_ingest`, `rag_ingest_base64`, `rag_ingest_url`, `rag_list`, `rag_delete`, `rag_reindex`, `rag_update_metadata`, `rag_snapshot`, `rag_stats` entries and one-line WHEN guidance for each; the existing `memory` SKILL.md MUST be updated with the RAG-vs-Memory disambiguation per FR-033.
- **FR-048**: On ingest completion, NetClaw's confirmation MUST teach usage: what was learned, and an example question the user could now ask.

#### Document Management (FR-050 – FR-054)

- **FR-050**: `rag_list` MUST return all indexed documents with full metadata; `rag_stats` MUST return corpus totals (docs, chunks, disk usage, model names, collections).
- **FR-051**: `rag_delete(document_id)` MUST remove a document's chunks from both the dense and keyword indexes and record the deletion in GAIT.
- **FR-052**: `rag_reindex(document_id)` MUST re-chunk and re-embed from the retained source file (originals kept under `~/.openclaw/rag/sources/`), used when chunking/embedding configuration changes.
- **FR-053**: Deleting or re-indexing MUST require the agent to confirm with the user when triggered conversationally (human-in-the-loop gate for destructive corpus operations).
- **FR-054**: The corpus MUST survive restarts and upgrades of `rag-mcp` (all indexes, source files, and metadata persist; a version marker enables migration).

#### HUD Knowledge Panel (FR-060 – FR-063)

- **FR-060**: The HUD MUST gain a **Knowledge** panel: upload area (drag-drop + picker) and an indexed-documents table (title, doc_type, source, pages, chunks, ingest date) rendered from `rag_list`, with no hardcoded data.
- **FR-061**: Each row MUST offer delete and re-index actions (with confirm dialogs) wired to `rag_delete`/`rag_reindex`.
- **FR-062**: The panel MUST show live ingestion progress states (parsing → chunking → embedding → done) and surface ingestion errors verbatim.
- **FR-063**: Snapshot collections MUST render in a visually distinct section with capture timestamp and age badge (staleness always visible, per GP-5).

#### Snapshots — `rag_snapshot` (FR-070 – FR-075)

- **FR-070**: `rag_snapshot(label, content, source_description)` MUST vectorize supplied live-output text (structured or raw show-command output) into a NEW collection named `snapshot_<label>_<ISO8601>` — never into `documents`.
- **FR-071**: `rag_snapshot` MUST NEVER be invoked automatically, from a heartbeat, or as a side effect. SKILL.md MUST state this prohibition; conversational invocation requires explicit human confirmation of scope before execution (human-in-the-loop gate).
- **FR-072 (Secret scrubbing)**: Before vectorization, snapshot content MUST pass a scrubber that redacts: passwords/enable secrets (incl. type 5/7/8/9 strings), SNMP community strings, TACACS/RADIUS keys, BGP/OSPF auth keys, pre-shared keys, and usernames when adjacent to secrets. Redactions are replaced with `<REDACTED:type>` and counted by type in the confirmation message (a zero count is reported explicitly).
- **FR-073**: Snapshot chunks MUST carry capture timestamp, device/source identifiers, and the command(s) that produced the data.
- **FR-074**: `rag_list` and the HUD MUST show snapshots separately from documents, with age; snapshots MUST be deletable, and a configurable retention policy (default: warn at 90 days, never auto-delete) MUST flag stale snapshots.
- **FR-075**: SKILL.md MUST frame snapshots as the ONLY sanctioned RAG use of live data, for explicit point-in-time comparison ("compare against last month's snapshot"), never as a substitute for a live MCP query.

#### Evaluation & Observability (FR-080 – FR-083)

- **FR-080**: The repo MUST define a **golden question set format** (question, expected source document, key answer facts) and ship the evaluation harness — but MUST NOT ship fixture documents. The operator supplies their own documents and a golden set (target: ≥ 20 Q&A pairs over 2–3 docs) after collecting real material; documentation MUST explain how to author one.
- **FR-081**: The automated test harness MUST measure, against a supplied golden set: retrieval hit-rate (expected doc in top-k), rerank lift (hit-rate with vs. without reranker), and a simple faithfulness check (answer facts present in retrieved chunks). Threshold: hit-rate ≥ 0.85 at k=5 to pass. When no golden set is present, the evaluation is skipped (reported as skipped, not passed); unit/integration tests of ingestion, chunking, search mechanics, and secret scrubbing still run using small inline test content.
- **FR-082**: The harness MUST run fully offline (models cached or a small stand-in model used); nothing in the test suite requires network access.
- **FR-083**: `rag_stats` MUST expose rolling retrieval telemetry (query count, mean latency, re-retrieval rate, low-confidence rate) for HUD display and self-diagnosis.

### Key Entities

- **Document**: A parsed source (PDF/MD/HTML/TXT/office formats/URL) with full metadata (title, source, doc_type, version, content hash, ingest timestamp, page/chunk counts) and a retained original for re-indexing. Always user-supplied (GP-7).
- **Chunk**: A structure-aware slice of a document with a heading-breadcrumb prefix, dual-indexed (semantic + keyword), carrying chunk ID, parent document ID, and page/section reference for citation.
- **Collection**: A named grouping of chunks — `documents` for knowledge, or `snapshot_<label>_<timestamp>` for opt-in live data. Never mixed in one search unless explicitly requested. Lives only in the RAG store, never in the Memory MCP's store.
- **Snapshot**: A timestamped, secret-scrubbed vectorization of explicitly requested live network output, carrying capture time, device/source identifiers, and originating commands; always staleness-tagged.
- **Golden set**: Operator-supplied, versioned Q&A pairs (question, expected source document, key answer facts) in a repo-defined format, driving the evaluation harness when present.
- **Retrieval log**: Per-query record: query text, collection, filters, chunk IDs returned, scores, latency, rounds used.
- **Knowledge-source hierarchy**: The documented routing model (parametric / Memory / RAG knowledge base / live MCP) encoded in SOUL.md and the `rag` + `memory` skills; not a data store itself, but the contract every answer's sourcing must obey.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user can upload a PDF via Slack, HUD, or URL and, in the same session, get a correctly cited answer sourced from it — with citation format per FR-044 — with ingestion of a 100-page document completing in under 5 minutes on the reference host.
- **SC-002**: Asked a fundamentals question, a live-state question, a past-session question, and an uploaded-document question (User Story 4), NetClaw routes each to its correct source (none / MCP / Memory / RAG) — verified in GAIT/retrieval logs with zero routing violations across a 20-question routing test.
- **SC-003**: Asked about content absent from the corpus, NetClaw says so (User Story 3) instead of hallucinating, within the 3-round budget, in 100% of tested honest-miss cases.
- **SC-004**: With an operator-supplied golden set in place, the evaluation harness runs fully offline and reports hit-rate@5 (pass threshold ≥ 0.85) and reranker lift over the fusion-only baseline; without one, the mechanics test suite (ingestion, chunking, search, scrubbing) passes in CI and the evaluation is explicitly reported as skipped.
- **SC-005**: A snapshot round-trip (User Story 7) shows per-type secret redaction counts at capture and a staleness age at retrieval, and never occurs without explicit confirmation — 100% of snapshot invocations gated in testing.
- **SC-006**: The entire system operates with zero network calls at query time and zero paid services, end to end (verified by running the full retrieval path with networking disabled).
- **SC-007**: Median knowledge-base search latency is under 2 seconds on a CPU-only reference host with a corpus of up to 5,000 chunks.
- **SC-008**: Every document in the corpus is listable with full metadata, deletable, and re-indexable by the user (GP-6), verified by exercising each management action end-to-end.
- **SC-009**: After the feature ships, the Memory MCP's store (`~/.openclaw/memory/`) is byte-for-byte unaffected by any RAG operation (ingest, search, delete, snapshot), and no RAG data appears in memory-tool results or vice versa.

## Assumptions

- **Embedding model default**: a small, fast English embedding model is the default (resolved from draft OQ-1); a larger, higher-recall model is a documented configuration upgrade. Model choice is configurable via environment.
- **URL crawl scope**: depth-1 same-domain crawl is supported at launch (resolved from draft OQ-2), always gated by a scope confirmation with a single-page fallback.
- **Format support**: wide format support at launch (resolved from draft OQ-3) via two tiers — modern XML-based office formats parsed directly; legacy binary formats via a free, local, offline conversion tool that the installer offers to install. OCR of scanned documents is out of scope for v1.
- **Memory MCP unchanged**: the existing Memory MCP (feature 033) and MemPalace continue to operate exactly as today; this feature only adds guidance-document updates (SOUL.md, `memory` SKILL.md disambiguation note) around them, no code changes to them.
- **Model cache sharing**: the RAG server may share the host's local model download cache with other components (models are read-only artifacts); data stores are never shared (FR-030).
- **Single operator**: NetClaw is single-operator; collection separation is organizational, not a security boundary (documented as such).
- **Reference host**: the existing NetClaw reference host (CPU-only acceptable); no GPU is required for any part of the system.
- **Initial model download**: embedding and reranker models are downloaded once at install time; air-gapped hosts pre-seed the model cache. After that, the system is fully offline.
- **Existing infrastructure reused**: the Slack attachment ingestion path reuses the packet-analysis pattern; the HUD panel extends the existing NetClaw HUD (`ui/netclaw-visual`); GAIT is already installed and operational.
- **Live network data** used in snapshots is produced by existing MCP servers (pyATS, etc.); this feature adds no new device-access capability.

## Out of Scope (explicit, deliberate)

- **GraphRAG / RAPTOR / knowledge-graph construction** — powerful but heavy for a free, offline, single-operator corpus; revisit if cross-document relationship queries become a demonstrated need.
- **Cloud embedding or reranking APIs** — violates GP-2.
- **Automatic ingestion of device configs, NetBox data, or any live system** — violates GP-1/GP-5. `rag_snapshot` is the only door, and it is human-opened.
- **Changes to the Memory MCP or MemPalace** — the agent-memory systems are untouched except for a disambiguation note in the `memory` skill's guidance (GP-7). No migration of memory data into RAG or vice versa.
- **Multi-tenant access control** — NetClaw is single-operator; collection separation is organizational, not a security boundary.
- **Fine-tuning or training on ingested documents** — retrieval only.
- **OCR of scanned/image-only documents** — v1 ingests extractable text only; scanned PDFs fail with a clear message.
- **Crawling beyond depth 1 or across domains** — deliberate bound on `rag_ingest_url`.
