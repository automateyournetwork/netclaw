# Phase 0 Research: Agentic RAG Knowledge Base (rag-mcp)

**Date**: 2026-07-16 | **Spec**: [spec.md](./spec.md)

All Technical Context unknowns resolved. Each decision below records what was chosen, why, and what was rejected.

## R1. Embedding model & wrapper

- **Decision**: `sentence-transformers` with default model `BAAI/bge-small-en-v1.5` (384-dim), overridable via `RAG_EMBEDDING_MODEL`. Queries get the BGE retrieval instruction prefix ("Represent this sentence for searching relevant passages: "); passages embedded bare. Documented upgrade: `BAAI/bge-base-en-v1.5` (768-dim).
- **Rationale**: Resolved with the user (spec Clarifications / draft OQ-1). bge-small is CPU-fast (~130 MB), strong on MTEB retrieval for its size, and fits the < 2 s p50 budget. sentence-transformers is already a repo dependency (memory-mcp), so no new framework.
- **Alternatives considered**: `all-MiniLM-L6-v2` (memory-mcp's model — weaker retrieval quality, no instruction tuning); `bge-base-en-v1.5` as default (better recall, ~3× slower on CPU — kept as documented upgrade); cloud embeddings (violates GP-2); deliberately **not** sharing memory-mcp's embedder instance — separate store, separate model choice (GP-7), though the HuggingFace model cache directory is naturally shared (read-only artifacts).

## R2. Vector store

- **Decision**: ChromaDB `PersistentClient` at `~/.openclaw/rag/chroma/`, `anonymized_telemetry=False`, cosine space (`hnsw:space: cosine`), one `documents` collection plus `snapshot_<label>_<ISO8601>` collections created on demand.
- **Rationale**: Exact pattern already proven in `mcp-servers/memory-mcp/storage/chroma_store.py`; free, embedded, offline, survives restarts. Separate persistence path enforces FR-030 physically.
- **Alternatives considered**: FAISS (no metadata filtering built in, more plumbing); LanceDB (fine but introduces a second vector-store idiom into the repo); Qdrant/Weaviate server (external service — violates GP-2 spirit and adds ops burden).

## R3. Keyword index

- **Decision**: `rank_bm25` (BM25Okapi), one index per collection, persisted as `~/.openclaw/rag/bm25/<collection>.pkl`, rebuilt on ingest/delete (FR-016). Tokenizer: lowercase whitespace split that **preserves punctuation-embedded networking tokens** (`Gi0/0/1`, `192.0.2.1/24`, `CVE-2026-1234`, `router bgp 65000`) as single tokens.
- **Rationale**: Pure-Python, tiny, offline; corpus ≤ 5k chunks makes in-memory BM25 trivial (rebuild cost negligible). Custom tokenizer is the whole point of the keyword leg — exact-match CLI/ID tokens (FR-021).
- **Alternatives considered**: SQLite FTS5 (viable, but BM25 ranking control and tokenizer customization are clumsier); Whoosh (unmaintained); Elasticsearch/OpenSearch (external service — rejected).

## R4. Fusion & reranking

- **Decision**: Each leg retrieves top-20; reciprocal rank fusion with standard k=60; fused top-20 reranked by cross-encoder `cross-encoder/ms-marco-MiniLM-L-6-v2` (default, `RAG_RERANKER_MODEL` override, `RAG_RERANK_ENABLED=true|false`) down to top-k. Scores below `RAG_RELEVANCE_FLOOR` (default 0.3 reranker sigmoid score; fusion-score fallback when reranker disabled) flag `low_confidence: true` rather than being dropped (FR-024).
- **Rationale**: RRF is parameter-light and robust for two-leg fusion; ms-marco-MiniLM-L-6 is the standard free CPU cross-encoder (~80 MB, ~50 ms/pair) — 20 pairs ≈ 1 s worst-case CPU, inside the 2 s budget. Disableable per FR-022.
- **Alternatives considered**: `BAAI/bge-reranker-base` (better quality, ~4× slower CPU — documented as upgrade next to the embedding upgrade); weighted score fusion (needs per-corpus tuning, fragile across score scales); no reranker (FR-081 must measure rerank lift, so the toggle exists anyway).

## R5. Document parsing (two-tier)

- **Decision**:
  - **PDF**: `pymupdf` — text with page numbers, TOC-based headings when present, font-size heuristic fallback for heading detection; tables extracted via pymupdf's table finder.
  - **Markdown**: native parse (heading/fence/table aware) — regex-based, no heavy dependency.
  - **HTML**: `beautifulsoup4` — heading hierarchy preserved, boilerplate (nav/footer/script) stripped.
  - **TXT**: paragraph-based, no headings.
  - **Modern office**: `python-docx` (DOCX: headings via styles, tables), `openpyxl` (XLSX: sheets→tables), `python-pptx` (PPTX: slide titles as headings), `vsdx` (VSDX: shape text per page).
  - **Legacy office (DOC/XLS/PPT/VSD)**: shell out to `soffice --headless --convert-to pdf` into a temp dir, then run the PDF path. Absence of `soffice` → graceful per-format failure with actionable message (FR-002).
- **Rationale**: All free, offline, pip-installable; pymupdf is the fastest maintained PDF extractor with page + TOC access (needed for FR-006 page counts and FR-014 page refs). LibreOffice conversion is the only realistic free path for 1990s binary formats and is already an apt-installable system package (repo precedent: spec 050 installs desktop apt packages).
- **Alternatives considered**: `pdfplumber` (better tables, much slower — rejected as primary; pymupdf tables suffice); `unstructured` (heavyweight, pulls large dependency tree); `mammoth` (DOCX→HTML, loses page fidelity vs python-docx styles); `textract` (unmaintained aggregator); OCR via tesseract (out of scope per spec).

## R6. Structure-aware chunking & token counting

- **Decision**: Custom chunker (`ingestion/chunker.py`): split on heading boundaries first, then paragraphs, target 400–800 tokens with 10–15% overlap; fenced code/CLI/config blocks and tables are atomic (oversized ones become standalone chunks); every chunk prefixed with `Document Title > Chapter > Section` breadcrumb before embedding (FR-010–012). Token counting uses the loaded embedding model's own tokenizer (already local — no new dependency, no network).
- **Rationale**: No off-the-shelf splitter honors "atomic CLI blocks + breadcrumbs" for networking docs; the logic is small and unit-testable. Using the embedder's tokenizer means chunk sizing matches what the model actually sees.
- **Alternatives considered**: LangChain `RecursiveCharacterTextSplitter` (character-based — prohibited by FR-010; drags in a framework); `tiktoken` (wrong tokenizer family for BGE; extra dep); fixed word counts (imprecise, but kept as the fallback if a tokenizer is unavailable in degraded mode).

## R7. Document registry & logs

- **Decision**: SQLite at `~/.openclaw/rag/rag.db` (stdlib `sqlite3`), tables: `documents` (metadata per FR-006 + `ingest_status` state machine for HUD progress + atomicity), `retrieval_log` (FR-025), `telemetry_rollup` (FR-083), `schema_version` (FR-054 migration marker). Snapshot collection metadata rows live in `documents` with `kind='snapshot'` + capture fields (FR-073).
- **Rationale**: Mirrors memory-mcp's SQLite+Chroma split; SQLite gives atomic transactions for the "all chunks committed or none" edge case (registry row flips to `ready` only after Chroma+BM25 writes complete; startup sweeps incomplete rows) and gives the HUD a read-only view without holding the MCP server hostage.
- **Alternatives considered**: JSON manifest files (no transactions, race-prone with HUD reads); storing all metadata only in Chroma (no atomic multi-index commit, awkward listing queries).

## R8. Slack ingestion path

- **Decision**: Mirror packet-analysis: a `rag_ingest_base64(filename, content_base64, doc_type?, title?)` tool saves into `~/.openclaw/rag/intake/` and runs the standard ingest pipeline; `rag_ingest(file_path, ...)` covers files already on disk. The `rag` SKILL.md documents the Slack workflow (attachment → download → base64 tool → in-thread confirmation) exactly like packet-analysis's `save_pcap_from_base64` flow, invoked via the existing `$MCP_CALL` helper convention.
- **Rationale**: Proven pattern in this exact deployment (packet-analysis SKILL.md); keeps one ingestion code path (FR-005) with two thin entry adapters.
- **Alternatives considered**: A Slack-side webhook service (new daemon, violates "reuse the packet-analysis pattern" in FR-003); passing raw file paths from Slack (attachments aren't on local disk).

## R9. URL ingestion & crawl confirmation

- **Decision**: `httpx` fetch + BeautifulSoup link extraction. Two-phase tool: `rag_ingest_url(url, mode="preview")` returns the page title + list/count of same-domain depth-1 links (no ingestion); after the agent confirms scope with the user, `rag_ingest_url(url, mode="ingest", include_linked=true|false)` performs it. Non-HTML content types dispatch to the matching parser (PDF at a URL → PDF path). A hard sanity bound (`RAG_CRAWL_MAX_PAGES`, default 30) truncates runaway link lists in the preview.
- **Rationale**: The preview/confirm split makes the FR-004 HIIL gate a *protocol* property (testable) instead of trusting agent behavior alone.
- **Alternatives considered**: `trafilatura` (great extraction but opinionated boilerplate removal can drop config blocks); single tool with `confirmed=true` flag (weaker: nothing forces a preview first — preview mode returns a scope token the ingest call must echo).

## R10. Secret scrubber

- **Decision**: Regex-based `scrubber.py` with a pattern table per secret class: Cisco type 5/7/8/9 hashes, `enable secret/password`, `username ... secret/password`, SNMP `community`, TACACS/RADIUS `key`, BGP/OSPF/ISIS `authentication` keys and `key-string`, IPsec/IKE `pre-shared-key`, Juniper `$9$...`, generic `password <string>`. Replacement `<REDACTED:type>`; per-type counts returned (zero counts reported explicitly). Runs on every `rag_snapshot` before chunking (FR-072).
- **Rationale**: Deterministic, offline, unit-testable per class; multi-vendor patterns are well-known text shapes.
- **Alternatives considered**: `detect-secrets`/truffleHog entropy scanners (tuned for source code, noisy on configs, miss type-7 style fields); LLM-based redaction (non-deterministic, violates the "scrubber must be verifiable" intent).

## R11. HUD integration

- **Decision**: Extend `ui/netclaw-visual/server.js` with REST endpoints `/api/rag/documents` (GET), `/api/rag/stats` (GET), `/api/rag/upload` (POST multipart via `multer` → saves to `~/.openclaw/rag/intake/` → invokes `rag_ingest`), `/api/rag/documents/:id` (DELETE) and `/api/rag/documents/:id/reindex` (POST) — both requiring a `confirm=true` body flag (FR-061 confirm dialogs). All endpoints (reads and mutations) go through the existing MCP-call child-process helper — one uniform access path, no native Node SQLite dependency. Ingestion progress: server polls `rag_list` while any ingest is non-terminal and pushes `rag_progress` / `rag_update` events through the existing `broadcastWS()` at `/ws`. New `src/panels/KnowledgePanel.js` follows the TwitterPanel class convention (constructor takes the shared socket, `render()`/`getTemplate()`/`setupEventListeners()`), with a distinct snapshot section + age badges (FR-063).
- **Rationale**: server.js already reads local state files and broadcasts over `/ws` on a poll timer — the registry-polling approach is its native idiom; the scout confirmed no upload path exists, so `multer` is the one new Node dependency.
- **Alternatives considered**: HUD calling the MCP server over a new HTTP transport (rag-mcp would need dual transports — more surface, against stdio convention); embedding upload logic in the panel via base64 JSON (breaks on 100 MB cap; multipart is correct).

## R12. Installer & registration

- **Decision**: Catalog entry `"rag-mcp|Platform Services|RAG Knowledge Base|Offline document knowledge base — hybrid retrieval, citations, opt-in snapshots (ChromaDB + BM25 + local reranker)"`; `component_install_rag_mcp()` does `pip3 install -e mcp-servers/rag-mcp` (with `--break-system-packages` fallback per repo pattern), creates `~/.openclaw/rag/`, pre-downloads embedding + reranker models (warns ~250 MB first run), offers `libreoffice` apt install for legacy formats (skippable), and — unlike memory-mcp — **registers in `config/openclaw.json`** (default-on per clarification) using the standard stdio entry: `command: "python3"`, `args: ["-u", "mcp-servers/rag-mcp/rag_mcp_server.py"]`, env `RAG_DATA_DIR`, `RAG_EMBEDDING_MODEL`, `RAG_RERANKER_MODEL`, `RAG_RERANK_ENABLED`, `RAG_MAX_DOC_MB`, `RAG_MAX_DOC_PAGES`, `RAG_CRAWL_MAX_PAGES`, `RAG_SNAPSHOT_WARN_DAYS` with `${VAR:-default}` interpolation. Added to `PROFILE_RECOMMENDED`.
- **Rationale**: Clarification Q4 fixed default-on with install-time model download; suzieq-mcp is the registration template; Principle XI enumerates every artifact.
- **Alternatives considered**: uvx-based registration like memory-mcp's printed command (memory-mcp is deliberately unregistered — our clarification says default-on, so openclaw.json is the right home); bundling LibreOffice unconditionally (large; optional step respects lean installs).

## R13. Evaluation harness (golden set operator-supplied)

- **Decision**: `tests/integration/test_rag_eval.py` loads `tests/fixtures/rag/golden_set.yaml` if present (format documented by a shipped `golden_set.example.yaml`: `question`, `expected_doc`, `answer_facts[]`, optional `doc_type_filter`); when absent, the module `pytest.skip`s with an explicit "no golden set supplied" message (reported skipped, never passed — FR-081). Metrics: hit-rate@5 (≥ 0.85 pass), rerank lift (same run with reranker toggled), faithfulness (each `answer_facts` substring present in retrieved chunks). Unit/integration mechanics tests use the memory-mcp offline pattern: mocked embedder (`MagicMock`) or a deterministic hash-based stand-in vectorizer + `tempfile` stores — zero model/network dependency.
- **Rationale**: Clarification Q3 — no fixture documents ship; the operator authors the golden set after collecting real docs. The example-file + skip design keeps CI green and honest.
- **Alternatives considered**: Synthetic auto-generated fixtures (user explicitly declined shipping docs); ragas/deepeval frameworks (LLM-judge dependencies — not offline/free).

## R14. GAIT + guidance documents

- **Decision**: Reuse memory-mcp's `gait_log()` graceful-degradation pattern (import `gait.repo`, log event, swallow-and-continue if absent) for ingest/delete/reindex/snapshot/search-summary events. Guidance updates: `SOUL.md` gains a `### Knowledge Base (RAG) Skills (1)` subsection + a "four knowledge sources" rule block under `## How You Work` (parametric / Memory / RAG / live MCP with routing rules and GP-1+GP-7 as beliefs, FR-032/033/047); `workspace/skills/rag/SKILL.md` carries the full agentic protocol (WHEN-to-retrieve, self-critique, 3-rounds-per-sub-query budget, citation format, snapshot prohibition); `workspace/skills/memory/SKILL.md` gains one disambiguation note; `TOOLS.md` gets the short entry, `TOOLS-REFERENCE.md` the detailed section (memory-mcp section as template); README counts bumped.
- **Rationale**: Scout confirmed exact insertion points and formats; agentic behavior lives in guidance because retrieval-as-a-tool (GP-3) means the model, not code, runs the loop — the code only enforces hard limits (budget cap is also enforced server-side per rolling question via the `rounds` parameter contract).
- **Alternatives considered**: Enforcing the iteration budget purely in SKILL.md prose (unverifiable — the tool contract's optional `round`/`sub_query_id` logging fields make budget adherence auditable in the retrieval log instead).
