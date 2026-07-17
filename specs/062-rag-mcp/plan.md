# Implementation Plan: Agentic RAG Knowledge Base (rag-mcp)

**Branch**: `062-rag-mcp` | **Date**: 2026-07-16 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/062-rag-mcp/spec.md`

## Summary

Build a standalone, fully offline FastMCP server (`rag-mcp`) that gives NetClaw a user-curated document knowledge base: multi-format ingestion (Slack attachment / HUD upload / URL with confirmed depth-1 crawl), structure-aware chunking with breadcrumb prefixes, hybrid dense+BM25 retrieval fused by reciprocal rank fusion and reranked by a local cross-encoder, mandatory citation metadata on every result, and an opt-in secret-scrubbed snapshot facility for point-in-time live-output comparison. Alongside the server: a new `rag` skill, SOUL.md/TOOLS.md/memory-skill guidance updates encoding the four-source knowledge hierarchy (parametric / Memory MCP / RAG / live MCP), a net-new HUD Knowledge panel with upload + corpus management, installer catalog integration (default-on), and an offline evaluation harness whose golden set is operator-supplied.

Technical approach: mirror the proven `memory-mcp` architecture (FastMCP + ChromaDB PersistentClient + sentence-transformers + SQLite registry + GAIT logging + editable pip install via the modular installer) in a **completely separate store** at `~/.openclaw/rag/` — per GP-7 the two systems share only the model-cache concept, never data.

## Technical Context

**Language/Version**: Python 3.10+ (server, matching repo MCP convention; memory-mcp packaging style with hatchling pyproject), Node.js 18+/ES2022 (HUD panel + Express endpoints), Bash (installer step)
**Primary Dependencies**: `fastmcp`/`mcp`, `chromadb>=0.4`, `sentence-transformers>=2.2` (+ `torch` CPU), `rank_bm25`, `pymupdf` (PDF), `beautifulsoup4` + `httpx` (HTML/URL), `python-docx`, `openpyxl`, `python-pptx`, `vsdx` (modern office), LibreOffice headless (`soffice`, optional system package) for legacy DOC/XLS/PPT/VSD conversion
**Storage**: `~/.openclaw/rag/` — ChromaDB (`chroma/`, dense vectors), SQLite (`rag.db`: document registry, retrieval log, telemetry, schema version), BM25 pickles (`bm25/<collection>.pkl`), retained originals (`sources/`), intake dir (`intake/`). Never touches `~/.openclaw/memory/` (FR-030)
**Testing**: pytest under `tests/unit/` + `tests/integration/` following `test_memory_mcp.py` conventions (sys.path insertion, `tempfile` data dirs, mocked embedder for offline runs); evaluation harness skips when no operator-supplied golden set exists (FR-081)
**Target Platform**: Linux (WSL2 reference host), CPU-only; air-gap capable after install-time model download
**Project Type**: MCP server + skill/docs + HUD extension (NetClaw capability addition per Constitution XI)
**Performance Goals**: `rag_search` p50 < 2 s at ≤ 5,000 chunks CPU-only (FR-026/SC-007); 100-page PDF ingested end-to-end < 5 min (SC-001)
**Constraints**: Zero network calls at query time, zero paid services (GP-2/SC-006); per-document soft cap 100 MB / 1,000 pages, configurable (FR-008a); reranker disableable for low-resource hosts (FR-022); atomic per-document ingestion (edge case: restart mid-ingest)
**Scale/Scope**: Single operator; corpus target ≤ 5,000 chunks (≈ tens of documents); 9 MCP tools; 1 new skill + 2 guidance-doc updates; 1 new HUD panel + ~4 Express endpoints

## Constitution Check

*GATE: evaluated against NetClaw Constitution v1.2.0 — PASS (pre-research and post-design). No violations to justify; Complexity Tracking left empty.*

| # | Principle | Compliance |
|---|-----------|------------|
| I / II | Safety-first, read-before-write | No device interaction. Snapshot content is *supplied* by existing MCP flows; rag-mcp itself never touches devices. Destructive corpus ops (`rag_delete`, `rag_reindex`) are HIIL-gated (FR-053). |
| IV | Immutable audit trail | Every ingest/delete/re-index/snapshot GAIT-committed (FR-009, FR-025); reuse memory-mcp's `gait_log()` graceful-fallback pattern. |
| V | MCP-native | FastMCP stdio server, standard JSON-RPC lifecycle; 9 tools. |
| VI | Multi-vendor neutrality | Content-agnostic; secret scrubber patterns cover multi-vendor syntaxes (Cisco/Juniper/Arista) in one server because scrubbing is generic text processing, not device logic. |
| VII / XII | Skill modularity + docs | One new `rag` skill with SKILL.md; `memory` SKILL.md gains only a disambiguation note; server ships README.md with tool inventory. |
| IX | Security by default | No credentials required; secret scrubbing (FR-072); write ops flagged and gated; local-only data. |
| X | Observability | `rag_stats` telemetry (FR-083), retrieval log, HUD Knowledge panel with live progress states. |
| XI | Full-stack artifact coherence | All touchpoints planned: README, catalog.sh, install-steps.sh, verify-catalog-coverage, HUD, SOUL.md, SKILL.md, .env.example, TOOLS.md + TOOLS-REFERENCE.md, config/openclaw.json. See checklist in tasks phase. |
| XIII | Credential safety | Only non-secret config env vars (paths, model names, flags); documented in .env.example. |
| XIV | HIIL external comms | Slack confirmations happen in already-established ingestion threads; no new autonomous outbound messaging. |
| XV | Backwards compatibility | New deps isolated in `mcp-servers/rag-mcp/pyproject.toml` (editable install, memory-mcp pattern); Memory MCP untouched (SC-009); no shared interface changes. |
| XVI | Spec-driven | This plan follows spec 062 (ratified, clarified 2026-07-16). |
| XVII | Milestone blog | WordPress draft scheduled post-implement. |

## Project Structure

### Documentation (this feature)

```text
specs/062-rag-mcp/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   ├── rag-mcp-tools.md # MCP tool contracts (9 tools)
│   └── hud-rag-api.md   # HUD Express endpoint + WS event contracts
└── tasks.md             # Phase 2 output (/speckit.tasks — NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
mcp-servers/rag-mcp/
├── rag_mcp_server.py          # FastMCP entry point, 9 tools, GAIT logging
├── ingestion/
│   ├── __init__.py
│   ├── parsers.py             # Format dispatch: PDF/MD/HTML/TXT native; docx/xlsx/pptx/vsdx; soffice fallback
│   ├── chunker.py             # Structure-aware chunking, atomic blocks, breadcrumbs (FR-010–012)
│   └── url_fetcher.py         # URL fetch + depth-1 same-domain link discovery (FR-004)
├── retrieval/
│   ├── __init__.py
│   ├── hybrid.py              # Dense + BM25 legs, RRF fusion (FR-021)
│   └── reranker.py            # Cross-encoder rerank, disableable (FR-022)
├── storage/
│   ├── __init__.py
│   ├── registry.py            # SQLite: documents, retrieval log, telemetry, schema version
│   ├── chroma_store.py        # PersistentClient, documents + snapshot_* collections
│   └── bm25_store.py          # rank_bm25 index per collection, pickle persistence (FR-016)
├── embeddings/
│   ├── __init__.py
│   └── embedder.py            # sentence-transformers wrapper, env-configurable model (FR-013)
├── scrubber.py                # Secret redaction for snapshots (FR-072)
├── pyproject.toml             # netclaw-rag-mcp, hatchling, console script
└── README.md                  # Tool inventory, env vars, transport, install

workspace/skills/rag/SKILL.md              # Agentic retrieval + ingestion + snapshot guidance (FR-040–048)
workspace/skills/memory/SKILL.md           # + RAG-vs-Memory disambiguation note (FR-033)

ui/netclaw-visual/
├── server.js                  # + /api/rag/* endpoints (list/stats/upload/delete/reindex) + WS rag_* events
└── src/panels/
    ├── KnowledgePanel.js      # Upload area, documents table, snapshot section (FR-060–063)
    └── KnowledgePanel.css

scripts/lib/catalog.sh         # + "rag-mcp|Platform Services|RAG Knowledge Base|..." entry + profile membership
scripts/lib/install-steps.sh   # + component_install_rag_mcp() (pip editable install, model pre-download, optional soffice)

tests/
├── unit/
│   ├── test_rag_chunker.py    # Structure-aware chunking, atomic blocks, breadcrumbs
│   ├── test_rag_scrubber.py   # All secret classes, zero-count reporting
│   └── test_rag_parsers.py    # Format dispatch, size cap, dedupe hash
├── integration/
│   ├── test_rag_mcp.py        # Tool round-trips with mocked embedder + tempdir store
│   └── test_rag_eval.py       # Golden-set harness: hit-rate@5, rerank lift, faithfulness; skips w/o golden set
└── fixtures/rag/
    └── golden_set.example.yaml  # Format documentation only — NO fixture documents shipped (clarified)

SOUL.md, TOOLS.md, TOOLS-REFERENCE.md, README.md, .env.example, config/openclaw.json  # coherence updates
```

**Structure Decision**: Single new Python package under `mcp-servers/rag-mcp/` mirroring `memory-mcp`'s layout (entry script + `storage/` + `embeddings/` submodules, hatchling pyproject, editable install), because that is the one proven in-repo pattern for a ChromaDB + sentence-transformers FastMCP server and the installer/test conventions already fit it. HUD work extends the existing Vite app in place (new panel class + server.js endpoints) — the established TwitterPanel/WS pattern. No `src/` top-level tree is used; this repo organizes by capability, not by layer.

## Complexity Tracking

*No constitution violations — table intentionally empty.*
