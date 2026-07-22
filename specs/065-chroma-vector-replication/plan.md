# Implementation Plan: Chroma-to-Chroma Vector Replication over eN2N

**Branch**: `065-chroma-vector-replication` | **Date**: 2026-07-22 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/065-chroma-vector-replication/spec.md`

## Summary

Let a claw pull a consenting peer's already-embedded RAG collection (feature 062) directly
into its own local Chroma store — vectors, chunk text, and metadata copied as-is via
`ChromaStore.add_chunks()`, with no re-embedding — so replicated knowledge is queryable
locally and offline. Builds on feature 064: the capability card gains an `embedding_model`
field per collection (064 doesn't advertise this today) so compatibility is checkable before
any transfer starts; replication requires its own distinct per-peer grant (`target_type
="knowledge_replica"`) separate from 064's query-only grant; and the job runs as an
asynchronous background task, reusing the existing `TaskManager`/`delegated_task`
infrastructure from feature 053 as-is. Two new low-level wire methods
(`n2n/knowledge/replicate_manifest`, `n2n/knowledge/replicate_batch`) let the receiver pull a
collection page by page over the existing NCFED channel, gated by the new grant and possession
tier. Replicas get a stable local identity derived from source peer + source `collection_id`
(never colliding across peers), are marked and stored distinctly from locally-authored
documents (a new `replica` value on the existing `documents.kind` enum), are excluded from the
receiver's own outbound knowledge advertisement by default, and are size-capped and fully
audited. No new MCP server, no new persistent store, no new wire method family.

## Technical Context

**Language/Version**: Python 3.10+ (daemon + `bgp/federation/*`, matching 052–064)
**Primary Dependencies**: Existing only — `bgp/federation/replication.py` (NEW: manifest/batch client+server logic, size-cap check, task worker), `tasks.py` (`TaskManager`/`delegated_task`, reused as-is for the async job), `authorization.py` (reused, new `target_type="knowledge_replica"` grant), `negotiate.py` (`TIER0_DENIED` gains `"knowledge/replicate"`), `channel.py` (existing `ch.call()` framing, already chunks messages >64 KB), `knowledge.py`/`inventory.py` (card gains `embedding_model`; `build_entries()` excludes `kind='replica'` rows), `bgp-daemon-v2.py` (new `/n2n/replicate*` HTTP routes, a fix to the `/n2n/tasks/<id>` status handler, and a grant/revoke audit fix, D12), `n2n-mcp/server.py` (three new MCP tools), rag-mcp's `storage/chroma_store.py` (gains a paginated collection-export read, an idempotent `upsert_chunks()` write path, and a rename-on-verify write path) and `storage/registry.py` (`documents.kind` gains `'replica'`; new nullable provenance columns). No new third-party packages.
**Storage**: Extends the existing rag-mcp `documents` table in `~/.openclaw/rag/rag.db` (feature 062) with a `'replica'` `kind` and new nullable columns (`source_peer_identity`, `source_collection_id`, `source_embedding_model`, `replicated_at`). Extends the existing Chroma store at `~/.openclaw/rag/chroma/` with one collection per replica, named from source peer + source `collection_id` (FR-016) — no new database, no new top-level store.
**Testing**: pytest under `tests/n2n/` (manifest/batch wire contract, grant-type isolation from query grants, mismatch refusal, size-cap refusal, task status/progress, replica identity/no-collision, re-sync full-replace semantics, non-advertisement of replicas, audit coverage) plus `tests/unit/test_rag_registry.py`-style coverage for the new `documents.kind='replica'` rows.
**Target Platform**: Linux (systemd `--user` mesh/member services), consistent with the live deployment.
**Project Type**: Extension of the existing NCFED daemon + capability card + RAG storage (single-project, in-repo).
**Performance Goals**: A book-sized collection (thousands of chunks) replicates via bounded batches (sized well under the channel's 64 KB per-frame / 16 MB per-message limits, `bgp/constants.py`); the triggering call itself returns in well under a second regardless of collection size (SC-007 — it only creates the task and returns a reference).
**Constraints**: Replication requires a distinct grant from query-retrieval (FR-002); embedding-model mismatch is refused before any byte of vector data is sent (FR-003, SC-002); a collection over the configured size cap is refused before transfer begins (FR-017, SC-008); an interrupted transfer never leaves a partially-queryable collection (FR-006); replicas never overwrite locally-authored collections and never collide across source peers (FR-016); replicas are not re-advertised or replicated onward without explicit opt-in (FR-009).
**Scale/Scope**: Small mesh of mutually-known operators (NCFED applicability); a handful of replicated collections per claw, each up to the configured size cap (default conservative, matching existing `RAG_MAX_DOC_MB`-style caps in feature 062).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Assessment |
|-----------|------------|
| IV. Immutable Audit Trail | PASS — every replication attempt, transfer, and re-sync is recorded via the existing `audit.record()`/GAIT path (FR-012), reusing 057/060/064's trail. Grant/revoke audit is a NEW, generic fix (research D12) — verified during `/speckit.analyze` that grants/revocations for *any* target_type were never audited before this feature; closing that gap is now in scope, not assumed pre-existing. |
| X. Observability as a First-Class Citizen | PASS (after remediation) — the HUD gains a replication-job panel (`ui/netclaw-visual/`) reflecting job status/progress, per the explicit constitutional requirement that new integrations appear in the HUD. |
| V. MCP-Native Integration | PASS — replication reads/writes rag-mcp's own storage layer (`chroma_store.py`, `registry.py`) directly, the same pattern feature 064's `knowledge.py` already uses ("cheapest path; no MCP spawn"); no bespoke integration outside the existing MCP-native storage. |
| VI. Multi-Vendor / Agent Neutrality | PASS — replication is a federation-daemon concern operating on a standard vector-store shape (ids/embeddings/texts/metadatas); nothing vendor- or agent-runtime-specific. |
| VII. Skill Modularity | PASS — replication logic lives in one new module (`replication.py`) with a single well-defined job; no duplication of `knowledge.py`'s advertisement/selection logic. |
| IX. Security by Default | PASS — default-deny, distinct grant type from query (FR-002), possession-tier only (`TIER0_DENIED` addition), size-capped (FR-017), no silent re-embedding/partial import (FR-003/006), replicas don't propagate onward without explicit opt-in (FR-009). |
| XIII. Credential Safety | PASS — no new credentials introduced; replication reuses existing peer identity/session material. |
| XV. Backwards Compatibility | PASS — additive card field (`embedding_model`); a peer that ignores it is unaffected; existing query-retrieval grants and behavior are untouched (FR-002 explicitly does not widen them). |
| XVI. Spec-Driven Development | PASS — this plan follows the clarified spec (065); no implementation without it. |
| XI. Full-Stack Artifact Coherence | PASS (after remediation) — an initial draft of this plan omitted `README.md`, `SOUL.md`, `TOOLS.md`, and `ui/netclaw-visual/` (the HUD), and its Project Structure omitted `bgp-daemon-v2.py`/`n2n-mcp/server.py` despite tasks modifying both; `/speckit.analyze` caught this (finding C1/I2) and the list below is now complete. |

No violations. Complexity Tracking not required.

## Project Structure

### Documentation (this feature)

```text
specs/065-chroma-vector-replication/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md         # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (manifest/batch wire contract + card field)
└── tasks.md             # Phase 2 (/speckit.tasks — not created here)
```

### Source Code (repository root)

```text
mcp-servers/protocol-mcp/bgp/federation/
├── replication.py       # NEW: manifest/batch server handlers + client pull loop (TaskManager
│                         #      worker) + size-cap check + local replica identity derivation
├── knowledge.py          # + embedding_model field in build_entries(); exclude kind='replica'
│                         #   rows from advertisement (FR-009)
├── inventory.py          # unchanged wiring — knowledge.py's extra field flows through as-is
├── invocation.py         # + register n2n/knowledge/replicate_manifest, n2n/knowledge/replicate_batch
│                         #   handlers (mirrors the existing handle_knowledge_query pattern)
├── authorization.py      # unchanged — new target_type "knowledge_replica" is just a new string,
│                         #   no schema change (grant/revoke/list already generic)
├── negotiate.py           # + "knowledge/replicate" added to TIER0_DENIED
├── tasks.py               # UNCHANGED — TaskManager/delegated_task reused as-is for the async job
├── audit.py               # unchanged — target_type="knowledge_replica" is just a new string
└── service.py             # + instantiate ReplicationManager; register the two new handlers

mcp-servers/protocol-mcp/bgp-daemon-v2.py   # + POST /n2n/replicate, /n2n/replicate/resync,
                                              #   DELETE /n2n/replicate/{peer}/{collection_id};
                                              #   + audit grant/revoke in /n2n/grants (D12);
                                              #   + skip outbound-poll for target_type=
                                              #   "knowledge_replicate" in the /n2n/tasks/<id> GET
                                              #   handler (load-bearing — see data-model.md)

mcp-servers/n2n-mcp/server.py   # + n2n_replicate, n2n_replicate_resync, n2n_replicate_delete
                                  #   tools; + n2n_grant docstring mentions 'knowledge_replica'

mcp-servers/rag-mcp/storage/
├── registry.py            # documents.kind CHECK gains 'replica'; new nullable columns
│                           #   (source_peer_identity, source_collection_id,
│                           #   source_embedding_model, replicated_at); schema_version bump
└── chroma_store.py        # + paginated collection export read (source side); + upsert_chunks()
                            #   for idempotent batch writes (D11); + staged-write / rename-on-
                            #   verify path (receiver side, FR-006)

mcp-servers/rag-mcp/rag_mcp_server.py   # rag_list() surfaces kind/provenance for replica rows

workspace/skills/n2n-federation/SKILL.md   # + replication trigger/status/re-sync/consent guidance,
                                            #   distinct from query-retrieval delegation
docs/ietf/draft-capobianco-ncfed-00.md     # §11 note staged for -01: card embedding_model field

README.md            # + replication capability description (Principle XI)
SOUL.md               # + replication capability summary (Principle XI)
TOOLS.md              # + n2n_replicate/_resync/_delete infrastructure reference (Principle XI)
ui/netclaw-visual/    # + HUD node/panel for replication job status (Principles X/XI)

tests/n2n/
├── test_replication_manifest_batch.py   # wire contract, grant isolation, mismatch refusal, size cap
├── test_replication_identity.py          # FR-016 cross-peer collision, no overwrite of local docs
├── test_replication_lifecycle.py         # async job status/progress, re-sync full-replace, revoke
└── test_replication_provenance.py        # FR-008/009 listing distinctness, non-advertisement
```

**Structure Decision**: Single-project, in-repo extension. A new
`bgp/federation/replication.py` holds the wire handlers and the client pull loop, reusing
`tasks.py`'s `TaskManager` unchanged for the async job (Phase 0 finding). `knowledge.py`
gains the `embedding_model` field and a `kind != 'replica'` advertisement filter.
`authorization.py`, `audit.py`, and `channel.py` are reused unchanged — replication only adds
new string values (`target_type`, `negotiate` operation name) they already treat generically.
rag-mcp's `registry.py`/`chroma_store.py` gain the replica-storage extensions. The daemon's HTTP
control plane (`bgp-daemon-v2.py`) and the operator-facing `n2n-mcp` tools are both extended —
these were missing from an earlier draft of this plan (`/speckit.analyze` finding I2) despite
being real, substantial touchpoints. README/SOUL/TOOLS/HUD updates are included per Constitution
Principle XI/X (also an `/speckit.analyze` finding, C1) — this feature does add operator-visible
capability (three new MCP tools, a new job type), so it is not exempt. No new package, MCP
server, wire method family, or top-level store.

## Complexity Tracking

No constitution violations — section intentionally empty.
