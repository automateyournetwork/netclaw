# Tasks: Agentic RAG Knowledge Base (rag-mcp)

**Input**: Design documents from `/specs/062-rag-mcp/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/rag-mcp-tools.md, contracts/hud-rag-api.md, quickstart.md

**Tests**: INCLUDED — the spec mandates an offline mechanics test suite (FR-081) and evaluation harness (FR-080–082). All Python tests follow the memory-mcp offline pattern: `sys.path` insertion, `tempfile.TemporaryDirectory` data dirs, mocked/stand-in embedder — zero model or network dependency.

**Organization**: Grouped by user story (US1–US7 from spec.md) for independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Parallelizable (different files, no dependency on incomplete tasks)
- **[Story]**: US1–US7 per spec.md

---

## Phase 1: Setup

**Purpose**: Package skeleton, dependencies, configuration surface

- [X] T001 Create `mcp-servers/rag-mcp/` package skeleton per plan.md: `ingestion/`, `retrieval/`, `storage/`, `embeddings/` subpackages each with `__init__.py`, plus empty `rag_mcp_server.py`, `scrubber.py`
- [X] T002 Create `mcp-servers/rag-mcp/pyproject.toml` (name `netclaw-rag-mcp`, hatchling, Python >=3.10, deps: `mcp`, `fastmcp`, `chromadb>=0.4.0`, `sentence-transformers>=2.2.0`, `torch>=2.0.0`, `rank_bm25`, `pymupdf`, `beautifulsoup4`, `httpx`, `python-docx`, `openpyxl`, `python-pptx`, `vsdx`; console script `rag-mcp-server = "rag_mcp_server:main"`; dev group `pytest`, `pytest-asyncio`) — mirror `mcp-servers/memory-mcp/pyproject.toml`
- [X] T003 [P] Create `mcp-servers/rag-mcp/config.py` reading all `RAG_*` env vars with contract defaults (`RAG_DATA_DIR=~/.openclaw/rag`, `RAG_EMBEDDING_MODEL=BAAI/bge-small-en-v1.5`, `RAG_RERANKER_MODEL=cross-encoder/ms-marco-MiniLM-L-6-v2`, `RAG_RERANK_ENABLED=true`, `RAG_RELEVANCE_FLOOR=0.3`, `RAG_MAX_DOC_MB=100`, `RAG_MAX_DOC_PAGES=1000`, `RAG_CRAWL_MAX_PAGES=30`, `RAG_SNAPSHOT_WARN_DAYS=90`, `RAG_MAX_ROUNDS=3`) and creating `rag/`, `chroma/`, `bm25/`, `sources/`, `intake/` dirs on startup
- [X] T004 [P] Add all `RAG_*` variables with descriptive comments (no values beyond defaults) to `.env.example`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Storage, embeddings, and server scaffold every story builds on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T005 Implement `mcp-servers/rag-mcp/storage/registry.py`: SQLite schema per data-model.md (`documents` incl. snapshot fields, `retrieval_log`, `telemetry_rollup`, `schema_version` starting at 1), `ingest_status` state machine (`pending→parsing→chunking→embedding→ready|error`), startup sweep of non-terminal rows to `error` with partial-index purge hooks, content-hash dedupe lookup
- [X] T006 [P] Implement `mcp-servers/rag-mcp/embeddings/embedder.py`: sentence-transformers wrapper with lazy load, env-configured model, BGE query-instruction prefix for queries (bare passages), tokenizer exposure for chunk sizing, graceful `MODELS_NOT_CACHED` error when model absent (no hang) — pattern: `memory-mcp/embeddings/embedder.py` but env-configurable
- [X] T007 [P] Implement `mcp-servers/rag-mcp/storage/chroma_store.py`: `PersistentClient` at `<RAG_DATA_DIR>/chroma` with `anonymized_telemetry=False`, cosine collections (`documents` + on-demand `snapshot_*`), add/query/delete-by-document, metadata per data-model.md chunk record
- [X] T008 [P] Implement `mcp-servers/rag-mcp/storage/bm25_store.py`: `rank_bm25` index per collection persisted to `<RAG_DATA_DIR>/bm25/<collection>.pkl`, full rebuild on ingest/delete, tokenizer preserving networking tokens (`Gi0/0/1`, `192.0.2.0/24`, `CVE-2026-1234`) as single tokens
- [X] T009 Implement `mcp-servers/rag-mcp/rag_mcp_server.py` scaffold: FastMCP app named `rag-mcp`, `success_response`/`error_response` envelope + error codes per contracts/rag-mcp-tools.md, `gait_log()` graceful-fallback helper (memory-mcp pattern), component wiring (config → registry → embedder → stores), startup integrity sweep, `main()` entry point
- [X] T010 [P] Write `tests/unit/test_rag_registry.py`: state-machine transitions, dedupe-hash uniqueness, startup sweep of interrupted ingestion, schema_version presence (tempdir SQLite, no models)

**Checkpoint**: Foundation ready — user story phases can begin

---

## Phase 3: User Story 1 — Ingest a document via Slack and get cited answers (P1) 🎯 MVP

**Goal**: File → parse → chunk → embed → dual-index → cited search result, with dedupe/re-index, GAIT commits, Slack base64 adapter (FR-001–003, FR-005–014, FR-044 citation string)

**Independent Test**: Ingest a sample PDF via `rag_ingest_base64`, verify confirmation payload (title, doc_type, pages, chunks, collection, example_question), then `rag_search` a fact unique to it and verify the `citation` string `[Title §sec, p.N — ingested YYYY-MM-DD]`; re-ingest same bytes → `deduplicated: true`; same title new bytes → `reindexed: true`

- [X] T011 [P] [US1] Implement `mcp-servers/rag-mcp/ingestion/parsers.py` (native tier): format dispatch by extension/magic, PDF via pymupdf (text + page numbers + TOC headings with font-size fallback + table extraction), Markdown (headings/fences/tables via regex parse), HTML via BeautifulSoup (heading hierarchy, boilerplate stripped), TXT (paragraphs); SHA-256 content hash; size-cap pre-check per FR-008a (`SIZE_LIMIT_EXCEEDED` with limit + override path in message); `UNSUPPORTED_FORMAT` / `PARSE_FAILED` (verbatim, incl. zero-extractable-text scanned PDFs)
- [X] T012 [P] [US1] Extend `parsers.py` (office tier): DOCX via python-docx (heading styles, tables), XLSX via openpyxl (sheets→tables), PPTX via python-pptx (slide titles as headings), VSDX via vsdx (shape text per page); legacy DOC/XLS/PPT/VSD via `soffice --headless --convert-to pdf` into tempdir then PDF path, `CONVERTER_UNAVAILABLE` with actionable message when `soffice` missing
- [X] T013 [P] [US1] Implement `mcp-servers/rag-mcp/ingestion/chunker.py`: heading-boundary-first then paragraph splits, 400–800 tokens via embedder tokenizer (word-count fallback), 10–15% overlap, atomic blocks (fenced code/CLI/config, tables) never split — oversized atomic block becomes its own chunk with `atomic=true`, breadcrumb prefix `Document Title > Chapter > Section` prepended before embedding (FR-010–012)
- [X] T014 [US1] Implement `rag_ingest` tool in `rag_mcp_server.py`: full pipeline (size check → parse → chunk → embed → Chroma+BM25 commit → registry flip to `ready` in one transaction), hash-match no-op with `deduplicated: true`, same-title-new-hash re-index (delete old chunks both indexes, inform via `reindexed: true`), original retained at `sources/<doc_id>/`, doc_type hint/default, GAIT commit describing what and why, `example_question` in response (FR-048)
- [X] T015 [US1] Implement `rag_ingest_base64` tool in `rag_mcp_server.py`: decode to `<RAG_DATA_DIR>/intake/<filename>`, delegate to the `rag_ingest` pipeline, `source` defaults to `slack:attachment` (packet-analysis `save_pcap_from_base64` pattern, FR-003)
- [X] T016 [US1] Implement `rag_search` v1 in `rag_mcp_server.py`: dense-leg search of a collection with k, SearchResult shape per contract including preformatted `citation` string (chunk IDs log-only per clarification), `corpus_empty` signal, `retrieval_log` write with chunk IDs/scores/latency (hybrid+rerank arrive in US2)
- [X] T017 [P] [US1] Create `workspace/skills/rag/SKILL.md` v1 following `workspace/skills/packet-analysis/SKILL.md` conventions: purpose, MCP tools table, Slack-attachment upload workflow (attachment → download → `rag_ingest_base64` via `$MCP_CALL` → in-thread confirmation), citation format rules, required env vars, example usage
- [X] T018 [P] [US1] Write `tests/unit/test_rag_parsers.py`: dispatch per format, size-cap rejection (FR-008a), hash stability, unsupported-format and empty-text errors (small inline/generated files, no fixture docs)
- [X] T019 [P] [US1] Write `tests/unit/test_rag_chunker.py`: heading-boundary splits, token targets and overlap, atomic code/config/table blocks never split, oversized-atomic standalone chunk, breadcrumb prefixes
- [X] T020 [US1] Write `tests/integration/test_rag_mcp.py`: ingest→search round trip with mocked embedder + tempdir store — confirmation payload fields, citation string format, dedupe no-op, changed-hash re-index, GAIT-helper no-crash when GAIT absent

**Checkpoint**: MVP — a document goes in via Slack path, a cited answer comes out

---

## Phase 4: User Story 2 — Agentic retrieval with self-critique (P1)

**Goal**: Hybrid BM25+dense retrieval with RRF fusion, cross-encoder reranking, metadata filters, low-confidence flagging, budget-auditable logging, and the agentic SKILL.md protocol (FR-020–027, FR-040–045)

**Independent Test**: With two docs ingested, scoped multi-part queries return fused+reranked results honoring `filters`; an exact CLI token (`Gi0/0/1`) findable via BM25 leg when embeddings miss it; sub-floor results carry `low_confidence: true`; `retrieval_log` records `round`/`sub_query_id`

- [X] T021 [P] [US2] Implement `mcp-servers/rag-mcp/retrieval/hybrid.py`: dense and BM25 legs each top-20, reciprocal rank fusion with k=60, stable tie-breaking
- [X] T022 [P] [US2] Implement `mcp-servers/rag-mcp/retrieval/reranker.py`: cross-encoder rerank of fused top-20 → top-k, `RAG_RERANK_ENABLED` toggle (fusion-score passthrough when off), relevance floor → `low_confidence: true` flag (flagged, never dropped — FR-024), CPU-only
- [X] T023 [US2] Upgrade `rag_search` in `rag_mcp_server.py` to full contract: hybrid+rerank pipeline, `filters` (doc_type, document_id, title, ingested_after/before → Chroma where-clauses + BM25 post-filter), `round`/`sub_query_id` logging params, latency measurement, p50 < 2 s target at ≤ 5k chunks
- [X] T024 [US2] Implement telemetry accumulation in `storage/registry.py`: query_count, mean_latency_ms, re_retrieval_rate (share of sub_query_ids with round > 1), low_confidence_rate — derived from `retrieval_log` for `rag_stats` (FR-083)
- [X] T025 [US2] Extend `workspace/skills/rag/SKILL.md` with the agentic protocol: WHEN-to-retrieve criteria (vendor procedures/customer standards/install steps YES; timeless fundamentals NO; live network state NEVER — route to MCPs; past sessions → Memory tools), query rewriting + decomposition into sub-queries, self-critique grading after every retrieval, hard budget 3 rounds **per sub-query** with stop-condition wording, synthesis discipline warning, citation-required rule (FR-040–045)
- [X] T026 [P] [US2] Write `tests/unit/test_rag_hybrid.py`: RRF math against hand-computed fixture, BM25 exact-token findability (`Gi0/0/1`, `CVE-2026-1234`, `router bgp 65000`) when dense leg is adversarially mocked to miss, reranker toggle passthrough
- [X] T027 [US2] Extend `tests/integration/test_rag_mcp.py`: filter scoping (doc_type-only search), low_confidence flagging at the floor, round/sub_query_id persisted in `retrieval_log`

**Checkpoint**: Both P1 stories done — knowledge loop with production retrieval quality

---

## Phase 5: User Story 3 — Honest miss on uncovered topics (P2)

**Goal**: The system gives the agent unambiguous "not covered" signal and the skill mandates honest reporting (FR-024, FR-041, US-5 acceptance)

**Independent Test**: Search an empty corpus → `corpus_empty: true`, no error; search for absent content → all results `low_confidence: true`; SKILL.md contains the honest-miss protocol verbatim

- [X] T028 [US3] Verify/finish honest-miss signals in `rag_mcp_server.py`: `corpus_empty` on empty collection (soft, never a crash), all-low-confidence result sets clearly distinguishable, deleted-chunk citation lookups fail gracefully (`NOT_FOUND`, no fabricated content)
- [X] T029 [US3] Extend `workspace/skills/rag/SKILL.md`: honest-miss protocol — grade chunks, refine within budget, then state the knowledge base does not cover it and offer ingestion; explicit prohibition on answering from irrelevant/low-confidence chunks (FR-041)
- [X] T030 [P] [US3] Extend `tests/integration/test_rag_mcp.py`: empty-corpus search returns `corpus_empty` cleanly; low-relevance query returns flagged results not silence

**Checkpoint**: Trust behavior — misses are honest and testable

---

## Phase 6: User Story 4 — Route each question to the right knowledge source (P2)

**Goal**: Guidance documents encode the four-source hierarchy so NetClaw affirmatively knows it has a knowledge base and what belongs to Memory vs RAG vs live MCP (FR-032/033/047, GP-1/GP-7)

**Independent Test**: SOUL.md contains the four-source routing block and RAG skill listing; `workspace/skills/memory/SKILL.md` contains the disambiguation note; TOOLS.md lists all 10 rag_* tools with WHEN one-liners

- [X] T031 [P] [US4] Update `SOUL.md`: add `### Knowledge Base (RAG) Skills (1)` subsection under `## Your Skills` (bump the skills/MCP counts in the header line), and add a "Four Knowledge Sources" routing block under `## How You Work` — parametric (timeless fundamentals) / Memory MCP (own past sessions, facts, decisions) / RAG knowledge base (user-uploaded documents — check it before declaring ignorance on vendor procedures, customer standards, install steps) / live MCP servers (current network state, NEVER answered from RAG) — with GP-1 and GP-7 stated as core beliefs
- [X] T032 [P] [US4] Update `workspace/skills/memory/SKILL.md`: add a disambiguation note — document-content questions and "remember this document" requests route to the `rag` skill (`rag_ingest`/`rag_search`); operational facts, session summaries, and decisions stay here; neither store writes into the other
- [X] T033 [P] [US4] Update `TOOLS.md` (short entry: 10 tools, one-line WHEN guidance each, data dir, no credentials) and `TOOLS-REFERENCE.md` (detailed section modeled on the Memory MCP section: tool groups, transport `stdio, fully offline`, `Data: ~/.openclaw/rag/ (SQLite + ChromaDB + BM25)`, env vars)
- [X] T034 [US4] Extend `workspace/skills/rag/SKILL.md` with a routing examples table (fundamentals → answer directly; "what was that BGP issue last month" → `memory_recall`; "what does our standard require" → `rag_search`; "current BGP state" → live MCP) and the ambiguous-source rule: both may be consulted but each claim attributed to its actual source (FR-032)

**Checkpoint**: NetClaw's guidance stack knows the knowledge base exists and what it is NOT

---

## Phase 7: User Story 5 — Ingest from a URL (P2)

**Goal**: Two-phase URL ingestion with structural depth-1 crawl-confirmation gate (FR-004)

**Independent Test**: `rag_ingest_url(mode="preview")` on a page with links returns same-domain depth-1 list + `scope_token`; `mode="ingest", include_linked=true` without a valid token → `SCOPE_TOKEN_INVALID`; with token → per-page ingest results each recording its URL as source

- [X] T035 [P] [US5] Implement `mcp-servers/rag-mcp/ingestion/url_fetcher.py`: httpx fetch with error surfacing (`FETCH_FAILED` verbatim), BeautifulSoup heading-preserving extraction, same-domain depth-1 link discovery capped at `RAG_CRAWL_MAX_PAGES` (truncation flagged), content-type dispatch (PDF-at-URL → PDF parser path)
- [X] T036 [US5] Implement `rag_ingest_url` tool in `rag_mcp_server.py` per contract: preview mode (title, linked_pages, scope_token — no ingestion), ingest mode (single page, or linked pages only with echoed valid scope_token), per-page `rag_ingest` pipeline reuse with URL recorded as source
- [X] T037 [US5] Extend `workspace/skills/rag/SKILL.md`: URL ingestion workflow — always preview first, present page count to the user, obtain explicit confirmation (single-page fallback always offered) before `mode="ingest"` with `include_linked=true`
- [X] T038 [P] [US5] Write `tests/unit/test_rag_url.py`: same-domain-only link discovery, cross-domain exclusion, cap truncation flag, scope-token enforcement (mocked httpx transport, inline HTML strings)

**Checkpoint**: All three ingestion entry points share one pipeline

---

## Phase 8: User Story 6 — HUD Knowledge panel + document management (P3)

**Goal**: Corpus visibility and management (GP-6, FR-050–054, FR-060–063): management tools, Express endpoints, WebSocket progress, panel UI

**Independent Test**: Upload via panel → progress chips parsing→chunking→embedding→done → row appears matching `rag_list` → delete with confirm dialog removes it from table and search; snapshots render separately with age badges

- [X] T039 [US6] Implement `rag_list` (kind-separated documents/snapshots arrays, full metadata; snapshots array returns empty until US7 lands — the `age_human`/`stale` snapshot fields are wired in by T049), `rag_stats` (corpus totals, disk usage, model names, collections, telemetry rollup), and `rag_update_metadata` (doc_type/title/version, registry + Chroma metadata sync) in `rag_mcp_server.py`
- [X] T040 [US6] Implement `rag_delete` and `rag_reindex` in `rag_mcp_server.py`: `confirmed=false` → confirmation-required notice (HIIL gate FR-053), delete removes chunks from Chroma AND BM25 + retained source + GAIT commit (FR-051), reindex re-runs pipeline from `sources/<doc_id>/` under current config (FR-052, `NOT_FOUND` for snapshots/missing source)
- [X] T041 [US6] Add `/api/rag/documents` (GET) and `/api/rag/stats` (GET) to `ui/netclaw-visual/server.js`, backed by invoking `rag_list`/`rag_stats` through the existing MCP-call child-process helper (uniform with mutations — amend the data-access note in `specs/062-rag-mcp/contracts/hud-rag-api.md` accordingly, avoiding a native Node SQLite dependency)
- [X] T042 [US6] (requires T045 first — multer must be installed) Add `POST /api/rag/upload` (multipart via multer → `~/.openclaw/rag/intake/` → `rag_ingest`, `202` + WS progress; `413` size cap with limit+override in body, `415` unsupported, `500` verbatim), `DELETE /api/rag/documents/:id` and `POST /api/rag/documents/:id/reindex` (both requiring `{confirm: true}`, `400` without) to `ui/netclaw-visual/server.js`
- [X] T043 [US6] Add `rag_progress`/`rag_update` WebSocket events to `ui/netclaw-visual/server.js` via existing `broadcastWS()`: poll `rag_list` on the existing interval while any document is in a non-terminal `ingest_status`, emit per-document status transitions and change notifications
- [X] T044 [P] [US6] Create `ui/netclaw-visual/src/panels/KnowledgePanel.js` + `KnowledgePanel.css` (TwitterPanel class convention: constructor takes shared socket, `render()`/`getTemplate()`/`setupEventListeners()`/`connectSocket()`): drag-drop + picker upload with client-side size pre-check, indexed-documents table (title, doc_type, source, pages, chunks, ingest date) rendered from `/api/rag/documents` with zero hardcoded data, per-row Delete/Re-index behind confirm dialogs, live progress chips from `rag_progress`, verbatim error display, visually distinct snapshot section with capture timestamp + age badge + stale flag; mount the panel in `ui/netclaw-visual/src/main.js`
- [X] T045 [US6] Add `multer` to `ui/netclaw-visual/package.json` dependencies and run `npm install` in `ui/netclaw-visual/`
- [ ] T046 [US6] Manual end-to-end HUD verification per quickstart.md: upload → progress → table → confirm-gated delete → snapshot section rendering; record results in the session GAIT log

**Checkpoint**: Users own the corpus — everything listable, inspectable, deletable, re-indexable

---

## Phase 9: User Story 7 — Opt-in snapshot of live network output (P3)

**Goal**: Secret-scrubbed, timestamped, staleness-tagged snapshot collections; opt-in only (FR-070–075, GP-5)

**Independent Test**: `rag_snapshot` with config text containing type-7 password + SNMP community returns per-type redaction counts (zeros reported); search of the snapshot collection returns `age_human` staleness string; snapshot listed separately with stale flag past 90 days

- [X] T047 [P] [US7] Implement `mcp-servers/rag-mcp/scrubber.py`: regex pattern table per secret class — Cisco type 5/7/8/9 hashes, enable secret/password, `username … secret/password`, SNMP `community`, TACACS/RADIUS `key`, BGP/OSPF/ISIS `authentication`/`key-string`, IPsec/IKE `pre-shared-key`, Juniper `$9$…`, generic `password <string>`, usernames adjacent to secrets — replacement `<REDACTED:type>`, per-type counts including explicit zeros (FR-072)
- [X] T048 [US7] Implement `rag_snapshot` tool in `rag_mcp_server.py`: scrub → device/command-aware chunking → embed into NEW `snapshot_<label>_<ISO8601>` collection (never `documents` — FR-070), registry row with `kind='snapshot'` + capture_ts/devices/commands/redaction_counts, GAIT commit, response with redaction report
- [X] T049 [US7] Implement staleness surfacing across `rag_mcp_server.py`: `capture_ts` + `age_human` ("captured 2026-07-16 14:02 UTC — 31 days ago") on every snapshot-collection `rag_search` result (FR-027) and `rag_list` entry, `stale: true` past `RAG_SNAPSHOT_WARN_DAYS` (warn only, never auto-delete — FR-074)
- [X] T050 [US7] Extend `workspace/skills/rag/SKILL.md` snapshot section: NEVER invoked automatically/heartbeat/side-effect (FR-071 prohibition verbatim), conversational HIIL scope confirmation before execution, lead answers with staleness + live-state-via-MCP reminder (FR-046), snapshots framed as the ONLY sanctioned RAG use of live data (FR-075)
- [X] T051 [P] [US7] Write `tests/unit/test_rag_scrubber.py` (every secret class redacted, counts correct, zero-count classes reported) and extend `tests/integration/test_rag_mcp.py` with a snapshot round trip (new collection created, never `documents`; staleness fields present; snapshot deletable)

**Checkpoint**: All seven user stories implemented

---

## Phase 10: Polish, Evaluation & Artifact Coherence (Constitution XI)

**Purpose**: Evaluation harness, installer integration, registration, docs, verification

- [X] T052 [P] Create `tests/fixtures/rag/golden_set.example.yaml` (format documentation: `question`, `expected_doc`, `answer_facts[]`, optional `doc_type_filter` — NO fixture documents, per clarification) and `tests/integration/test_rag_eval.py` (loads `tests/fixtures/rag/golden_set.yaml` if present else `pytest.skip("no golden set supplied")`; measures hit-rate@5 vs ≥ 0.85, rerank lift via toggle, faithfulness substring check; fully offline)
- [X] T053 [P] Create `mcp-servers/rag-mcp/README.md`: tool inventory (10 tools: name/description/params), env vars, transport (stdio), install steps, data layout, RAG-vs-Memory boundary statement (per MCP Server Standards)
- [X] T054 Add catalog entry `"rag-mcp|Platform Services|RAG Knowledge Base|Offline document knowledge base — hybrid retrieval, citations, opt-in snapshots (ChromaDB + BM25 + local reranker)"` to `scripts/lib/catalog.sh` and add `rag-mcp` to `PROFILE_RECOMMENDED`
- [X] T055 Add `component_install_rag_mcp()` to `scripts/lib/install-steps.sh`: `pip3 install -e "$MCP_DIR/rag-mcp"` with `--break-system-packages` fallback, create `~/.openclaw/rag/`, pre-download embedding + reranker models (warn ~250 MB first run), offer optional `libreoffice` apt install for legacy DOC/XLS/PPT/VSD (skippable), print registration status
- [X] T056 Register `rag-mcp` in `config/openclaw.json` `mcpServers` (default-on per clarification): `"command": "python3", "args": ["-u", "mcp-servers/rag-mcp/rag_mcp_server.py"]`, env block with `${RAG_*:-default}` interpolation per contract
- [X] T057 Run `python3 scripts/verify-catalog-coverage.py` and resolve any gaps between catalog, config, and docs
- [X] T058 [P] Update `README.md`: capability description, skill/MCP/tool counts, Knowledge Base section with setup pointer
- [X] T059 Final verification: full `pytest tests/unit/test_rag_*.py tests/integration/test_rag_mcp.py -v` green; re-run existing suites to prove no regression (`pytest tests/integration/test_memory_mcp.py -v` at minimum — Constitution XV); SC-006 spot check (retrieval path with network disabled via cached/mocked models); SC-009 check (`~/.openclaw/memory/` mtime/bytes unchanged by a full ingest/search/delete/snapshot cycle); `rag_search` p50 < 2 s sanity check on a synthetic 5k-chunk corpus; SC-001 ingestion-time check (synthetic ~100-page document ingests in < 5 min on this host)
- [ ] T060 Behavioral validation + milestone wrap-up: run the SC-002 routing validation against the live agent (a 20-question set spanning fundamentals / live-state / past-session / uploaded-doc questions, verifying source routing in GAIT/retrieval logs) and SC-003 honest-miss spot checks, recording results in the GAIT session summary; then draft the WordPress milestone blog post (what was built, why, key decisions, lessons — present to John for review before publishing, Constitution XVII)

---

## Dependencies & Execution Order

```text
Phase 1 (Setup) ──► Phase 2 (Foundational) ──► Phase 3 (US1, MVP)
                                                    │
                              ┌─────────────────────┤
                              ▼                     ▼
                        Phase 4 (US2)      Phase 6 (US4, docs-only — independent after US1 tool names exist)
                              │
                              ▼
                        Phase 5 (US3, builds on US2 signals)
                              │
        ┌─────────────────────┼──────────────────────┐
        ▼                     ▼                      ▼
  Phase 7 (US5)         Phase 8 (US6)          Phase 9 (US7)   ← mutually independent
        └─────────────────────┴──────────────────────┘
                              ▼
                     Phase 10 (Polish & Coherence)
```

- **US1 → US2**: `rag_search` v1 (T016) is upgraded in place by T023.
- **US2 → US3**: honest-miss signals depend on `low_confidence` (T022).
- **US4** (guidance docs) only needs final tool names — can run any time after Phase 3, fully parallel to US2/US3/US5/US7.
- **US5 / US6 / US7** are mutually independent once Phase 3 is done (US6's `rag_list` staleness fields for snapshots land in T049 but degrade gracefully — the panel's snapshot section simply renders empty until US7 ships).
- **Phase 10** requires everything (T057/T059 verify the whole).

## Parallel Execution Examples

- **Phase 2**: T006, T007, T008 (embedder, chroma_store, bm25_store — different files) after T005; T010 alongside.
- **Phase 3 (US1)**: T011, T012, T013, T017 in parallel; then T014 → T015 → T016; T018/T019 parallel with T014+.
- **After Phase 3**: one track takes Phase 4→5 (retrieval quality), a second track takes Phase 6 (T031, T032, T033 all [P] — three different doc files), a third starts Phase 7's T035.
- **Phase 8**: T039→T040 first; T045 (multer install) before T042; T044 (panel UI) in parallel with T041–T043 (server endpoints).
- **Phase 10**: T052, T053, T058 in parallel; T054→T055→T056→T057 sequential (installer chain).

## Implementation Strategy

**MVP first**: Phases 1–3 alone deliver User Story 1 — a document ingested via the Slack base64 path returning cited search results. That is demonstrable value and the natural first checkpoint.

**Incremental delivery**: Ship US2 (retrieval quality) next — together the two P1 stories are the real knowledge loop. US3+US4 (P2 trust/routing) are small and high-leverage. US5 (URL), US6 (HUD), US7 (snapshots) can land in any order or in parallel tracks. Phase 10 is the Constitution XI gate — the feature is not "done" until `verify-catalog-coverage.py` passes and every coherence artifact is updated.

**Task count**: 60 total — Setup 4, Foundational 6, US1 10, US2 7, US3 3, US4 4, US5 4, US6 8, US7 5, Polish 9.
