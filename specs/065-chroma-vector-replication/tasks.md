# Tasks: Chroma-to-Chroma Vector Replication over eN2N

**Input**: Design documents from `/specs/065-chroma-vector-replication/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Included — the spec's Success Criteria and quickstart.md call for pytest coverage,
and the repo is test-driven (`tests/n2n/`).

**Organization**: By user story (US1/US2 = P1, US3/US4 = P2), each independently testable.

> This revision incorporates `/speckit.analyze` remediation (2026-07-22): grant/revoke audit
> (D12), idempotent batch writes via upsert (D11), missing `[Story]` labels, missing
> README/SOUL/TOOLS/HUD touchpoints (Constitution XI/X), and three previously-untested
> success criteria (SC-001, SC-004 initial-replication path, FR-009's onward-block clause).
> Task IDs were renumbered from the pre-analysis draft; there is no prior implementation to
> reconcile against.

## Path Conventions

Single project, in-repo. Federation code: `mcp-servers/protocol-mcp/bgp/federation/` and
`mcp-servers/protocol-mcp/bgp-daemon-v2.py` (HTTP control plane). RAG storage:
`mcp-servers/rag-mcp/storage/`. Operator/agent tools: `mcp-servers/n2n-mcp/server.py`.
Tests: `tests/n2n/`. Skill docs: `workspace/skills/`. Draft: `docs/ietf/`. HUD: `ui/netclaw-visual/`.

---

## Phase 1: Setup

- [X] T001 Confirm the surfaces this feature reuses are callable as assumed: `TaskManager`/`delegated_task` (`fed.tasks` in `mcp-servers/protocol-mcp/bgp/federation/service.py`), `Authorizer.grant/authorize` (`fed.authz`), and the installed `chromadb` version's `Collection.modify(name=...)` rename and `Collection.upsert(...)` APIs (D7/D11). Record findings as a "D10 — reuse surfaces confirmed" note in `specs/065-chroma-vector-replication/research.md`.
- [X] T002 [P] Create empty test modules `tests/n2n/test_replication_manifest_batch.py`, `tests/n2n/test_replication_identity.py`, `tests/n2n/test_replication_lifecycle.py`, and `tests/n2n/test_replication_provenance.py`, each importing the shared `conftest.py` manager fixture so later test tasks just add cases.
- [X] T003 [P] Add `N2N_REPLICATION_MAX_CHUNKS` to `.env.example` with a description (conservative default, e.g. `20000`) per Constitution Principle XIII.

**Checkpoint**: Test scaffolding and config surface exist; nothing yet depends on implementation.

---

## Phase 2: Foundational (blocking prerequisites)

**Purpose**: Storage schema, storage primitives (including idempotent writes and grant/revoke audit), local identity derivation, and tier gating that every user story below depends on.

- [X] T004 Extend `mcp-servers/rag-mcp/storage/registry.py`: bump `SCHEMA_VERSION` to `2`; add `'replica'` to the `documents.kind` CHECK constraint; add nullable columns `source_peer_identity`, `source_collection_id`, `source_embedding_model`, `replicated_at`; add a migration step (guarded by the existing `schema_version` row) that runs `ALTER TABLE documents ADD COLUMN ...` for each new column and updates the CHECK-constrained `kind` values on existing installs going from version 1 to 2 (no such migration exists yet — this is new).
- [X] T005 [P] Add `ChromaStore.get_chunks_page(collection, offset, limit)` in `mcp-servers/rag-mcp/storage/chroma_store.py`: source-side paginated export returning `{ids, embeddings, documents, metadatas}` for one page via the underlying `coll.get(limit=, offset=)`.
- [X] T006 [P] Add `ChromaStore.promote_staging(staging_name, stable_name)` in `mcp-servers/rag-mcp/storage/chroma_store.py`: deletes `stable_name` if it already exists, then renames the staging collection to `stable_name` via `Collection.modify(name=...)` (D7's rename-on-verify step for re-sync).
- [X] T007 [P] Add `ChromaStore.upsert_chunks(collection, ids, embeddings, texts, metadatas)` in `mcp-servers/rag-mcp/storage/chroma_store.py`, using Chroma's `Collection.upsert()` instead of `add()` — writing the same batch twice must be a no-op, not an error or a duplicate (D11, fixes FR-005 idempotency). Replication's write path uses this method; local ingestion continues to use the existing `add_chunks()` unchanged.
- [X] T008 Create `mcp-servers/protocol-mcp/bgp/federation/replication.py` with a module-level `MAX_CHUNKS = int(os.environ.get("N2N_REPLICATION_MAX_CHUNKS", "20000"))` and a `local_replica_identity(peer_identity: str, source_collection_id: str) -> str` helper returning `f"replica__{peer_identity}__{source_collection_id}"` (D6/FR-016) plus a skeleton `ReplicationManager` class taking the `FederationService` instance.
- [X] T009 [P] Add `"knowledge/replicate"` to the `TIER0_DENIED` frozenset in `mcp-servers/protocol-mcp/bgp/federation/negotiate.py`, alongside the existing `"knowledge/query"`.
- [X] T010 Instantiate `self.replication = ReplicationManager(self)` in `FederationService.__init__` in `mcp-servers/protocol-mcp/bgp/federation/service.py`, alongside the existing `self.tasks = TaskManager(...)` / `self.invoker = Invoker(self)` lines.
- [X] T011 [P] Add `audit.record()` calls to the `/n2n/grants` POST and DELETE handlers in `mcp-servers/protocol-mcp/bgp-daemon-v2.py` (~lines 272-285): record `{direction="local", target_type=<the granted target_type>, target_name, decision="granted"|"revoked"}` on every grant/revoke, for every `target_type` — not a `knowledge_replica`-only special case (D12). This closes a pre-existing gap (verified during `/speckit.analyze`: no grant/revoke was ever audited, for any target type) that FR-012 requires closed for replication and that would otherwise be inconsistent to fix for only one grant type.

**Checkpoint**: Schema, idempotent storage primitives, identity derivation, tier gating, and grant/revoke audit are all in place and unit-testable without a live peer.

---

## Phase 3: User Story 1 — Discover whether a peer's collection is safe to replicate (Priority: P1)

**Goal**: A peer pulling the card can see a collection's embedding model before requesting anything.
**Independent test**: Ingest a doc, pull the card as a peer, confirm the knowledge entry names the embedding model, with no content added.

- [X] T012 [US1] Extend `build_entries()` in `mcp-servers/protocol-mcp/bgp/federation/knowledge.py`: add `embedding_model` (read from rag-mcp `config.EMBEDDING_MODEL`) to each returned entry and to `_SAFE_KEYS`; add `AND kind != 'replica'` to the registry `SELECT` so replicated rows never contribute to a claw's own advertised aggregation (FR-001, groundwork for FR-009).
- [X] T013 [P] [US1] Test in `tests/n2n/test_replication_manifest_batch.py`: the card's `knowledge` entries include `embedding_model`; `_assert_no_secrets` still passes; a `kind='replica'` row present in the registry does not appear in, or change the counts of, the claw's own advertised collections.

**Checkpoint**: US1 independently demonstrable — compatibility is checkable before any transfer.

---

## Phase 4: User Story 2 — Consented one-shot replication of a collection (Priority: P1)

**Goal**: A granted peer replicates a full collection's vectors/text/metadata into its own local Chroma store, with no re-embedding, as an asynchronous, retry-safe job.
**Independent test**: Grant `knowledge_replica` for a test collection between two claws with matching embedders, trigger replication, confirm local query results with zero embedder invocations during import.

- [X] T014 [US2] Implement `handle_replicate_manifest` in `mcp-servers/protocol-mcp/bgp/federation/invocation.py`: tier-0 denial (`negotiate.allows(..., "knowledge/replicate")`), no-existence-oracle visibility check (reuse `_load_knowledge`), `self.authz.authorize(peer, "knowledge_replica", collection_id)` default-deny, returns `{collection_id, embedding_model, chunk_count}` per `contracts/knowledge-replication.md`, audited with `target_type="knowledge_replica"`.
- [X] T015 [US2] Implement `handle_replicate_batch` in `mcp-servers/protocol-mcp/bgp/federation/invocation.py`: identical gating to T014, params `{collection_id, offset, limit}`, reads via `ChromaStore.get_chunks_page` (T005) plus registry document titles for chunk metadata, returns one page per the contract, audited per call.
- [X] T016 [US2] Register `n2n/knowledge/replicate_manifest` and `n2n/knowledge/replicate_batch` in both service handler maps in `mcp-servers/protocol-mcp/bgp/federation/service.py` (mirroring the existing `n2n/knowledge/query` registration in both the eN2N and iN2N maps).
- [X] T017 [US2] Implement client helpers `fetch_replicate_manifest(ident, collection_id)` and `fetch_replicate_batch(ident, collection_id, offset, limit)` in `invocation.py`, using `ch.call(...)`, mirroring the existing `query_remote_knowledge`.
- [X] T018 [US2] Implement `ReplicationManager.start(peer, collection_id)` in `replication.py`: creates the job via `self.service.tasks.create(direction="inbound", target_type="knowledge_replicate", target_name=collection_id, ...)` — `direction="inbound"` deliberately, so the `/n2n/tasks/<id>` status handler (T021) takes its local-read path rather than trying to poll a peer that never runs any task for us — then `self.service.tasks.run(task_id, worker)` and returns `task_id` immediately (FR-015).
- [X] T019 [US2] Implement the `worker(progress)` coroutine in `replication.py`: call T017's manifest fetch; refuse before any batch call if `embedding_model` mismatches the local config (FR-003) or `chunk_count > MAX_CHUNKS` (FR-017); otherwise loop `fetch_replicate_batch` in pages, on the first page call `registry.new_document(kind='replica', collection=local_replica_identity(peer, collection_id), ...)` and on every page write via `ChromaStore.upsert_chunks()` (T007 — not `add_chunks()`, so a retried page is a safe no-op), calling `progress(f"{received}/{total} chunks")` between pages; once the received count matches the manifest, call `registry.finalize(doc_id, chunk_count=received)` (FR-006/FR-007).
- [X] T020 [US2] Add `POST /n2n/replicate` (body `{peer, collection_id}` → `fed.replication.start(...)`, returns `{task_id}`) in `mcp-servers/protocol-mcp/bgp-daemon-v2.py`, mirroring the existing `/n2n/tasks` POST handler's shape and error handling.
- [X] T021 [US2] Extend the `/n2n/tasks/<id>` GET handler in `mcp-servers/protocol-mcp/bgp-daemon-v2.py` (~line 441): select `target_type` alongside `direction`/`peer_identity`/`state`, and skip the outbound-remote-poll branch whenever `target_type == "knowledge_replicate"` — replication jobs run entirely locally and have no peer-side `delegated_task` counterpart to poll.
- [X] T022 [P] [US2] Add `n2n_replicate(peer: str, collection_id: str) -> str` MCP tool in `mcp-servers/n2n-mcp/server.py` (`POST /n2n/replicate`); docstring states it returns a `task_id` immediately and to poll with the existing `n2n_task_status`/`n2n_task_result` tools — no new status/result tools are added (reuse per research D1).
- [X] T023 [P] [US2] Update the `n2n_grant` docstring in `mcp-servers/n2n-mcp/server.py` to mention `target_type='knowledge_replica'` as a distinct grant from `'knowledge'` (query-only) — following the same doc-only precedent as the recent `n2n_grant` docstring update for `'knowledge'` itself.
- [X] T024 [P] [US2] Test in `tests/n2n/test_replication_manifest_batch.py`: manifest/batch calls denied at tier-0; denied for a peer holding only a `knowledge` (query) grant on the same collection — no `knowledge_replica` grant; succeed for a possession-tier peer holding the `knowledge_replica` grant; a grant and a revoke each produce exactly one audit record (T011).
- [X] T025 [P] [US2] Test in `tests/n2n/test_replication_manifest_batch.py`: embedding-model mismatch and an over-cap `chunk_count` both refuse the job before any `replicate_batch` call is made (assert zero batch calls via a spy/mock on the client helper).
- [X] T026 [P] [US2] Test in `tests/n2n/test_replication_lifecycle.py`: `ReplicationManager.start` returns a `task_id` immediately without blocking; polling shows `queued`/`in-progress`/`complete` with chunk progress; a simulated mid-transfer failure leaves no `ready` `kind='replica'` row (FR-006).
- [X] T027 [P] [US2] Test in `tests/n2n/test_replication_identity.py`: two source peers each advertising a collection literally named `documents` replicate into two distinct, non-colliding local identities (T008); replicating into a name matching an existing locally-authored (`kind='document'`) collection never merges into or overwrites it.
- [X] T028 [P] [US2] Test in `tests/n2n/test_replication_lifecycle.py` (SC-001): mock/spy the embedder used by `worker` (T019); run a successful replication end-to-end and assert the embedder is invoked **zero** times during the entire import.
- [X] T029 [P] [US2] Test in `tests/n2n/test_replication_lifecycle.py` (SC-004, success path): a collection sized to require at least 3 batches replicates successfully; assert the receiver's final chunk count exactly matches the manifest's `chunk_count`, with no data loss and no duplication across batch boundaries.
- [X] T030 [P] [US2] Test in `tests/n2n/test_replication_manifest_batch.py` (FR-005 idempotency): call `fetch_replicate_batch` for the same `{offset, limit}` twice against the same job/collection (simulating a single-page retry, not a whole-job restart) and assert the receiver's stored chunk count and content are identical to a single successful call — no error, no duplicate ids (proves T007's `upsert_chunks()` closes the gap identified in `/speckit.analyze` finding U1).

**Checkpoint**: US2 independently demonstrable — a real, asynchronous, retry-safe, no-re-embedding replication works end-to-end, with the SC-001/SC-004 success paths and FR-005 idempotency now directly tested (not just structurally implied).

---

## Phase 5: User Story 3 — Manual re-sync when the source changes (Priority: P2)

**Goal**: An operator refreshes a previously replicated collection to match the current source snapshot, with no duplicates or stale chunks.
**Independent test**: Replicate, add a document at the source, re-sync, confirm the receiver's copy reflects the new document with no duplication of unchanged chunks.

- [X] T031 [US3] Implement `ReplicationManager.resync(peer, collection_id)` in `replication.py`: runs the same manifest/mismatch/cap checks as `start` (T019), but writes pages into a temporary staging Chroma collection via `upsert_chunks()` (T007); on verified completion, calls `ChromaStore.promote_staging()` (T006) and replaces the prior `kind='replica'` `documents` rows for this local identity with the freshly received set in one local transaction (D7 full-replace — no per-document diffing, matching the spec's explicit non-goal of partial replication).
- [X] T032 [US3] Add `POST /n2n/replicate/resync` (body `{peer, collection_id}`) in `bgp-daemon-v2.py`, wired to `fed.replication.resync(...)`, returning `{task_id}` the same way as T020.
- [X] T033 [P] [US3] Add `n2n_replicate_resync(peer: str, collection_id: str) -> str` MCP tool in `mcp-servers/n2n-mcp/server.py`, with the same "poll with `n2n_task_status`/`n2n_task_result`" guidance as T022.
- [X] T034 [P] [US3] Test in `tests/n2n/test_replication_lifecycle.py`: after a source-side document addition, re-sync yields a receiver-side chunk count and content that exactly matches the new source snapshot, with no duplicate or stale chunks from the prior version (SC-006).
- [X] T035 [P] [US3] Test in `tests/n2n/test_replication_lifecycle.py`: revoking the `knowledge_replica` grant between an initial replication and a later re-sync attempt refuses the re-sync (audited) while the existing local replica remains untouched and still queryable.

**Checkpoint**: US3 independently demonstrable — replicas can be kept current without drifting or duplicating.

---

## Phase 6: User Story 4 — Replica provenance, isolation, and cleanup (Priority: P2)

**Goal**: Replicas are visibly distinct with correct provenance, never silently re-shared or re-replicated onward, and cleanly deletable.
**Independent test**: Replicate, list local collections and confirm provenance/distinctness, confirm non-advertisement and non-replicability to a third peer, delete and confirm full removal.

- [X] T036 [US4] Add a local listing surface for replicas: extend `rag_list()` in `mcp-servers/rag-mcp/rag_mcp_server.py` to include `kind`, `source_peer_identity`, `source_collection_id`, and `replicated_at` for `kind='replica'` rows, so they are visibly distinguishable from `kind='document'` rows in any existing listing consumer (FR-008).
- [X] T037 [US4] Implement `ReplicationManager.delete(peer, collection_id)` in `replication.py`: removes every `documents` row for the derived local identity (T008) and drops the corresponding Chroma collection; add `DELETE /n2n/replicate/{peer}/{collection_id}` in `bgp-daemon-v2.py` and `n2n_replicate_delete(peer: str, collection_id: str) -> str` in `mcp-servers/n2n-mcp/server.py`.
- [X] T038 [US4] Confirm the T012 `kind != 'replica'` advertisement filter fully satisfies FR-009's first clause (a replica is never re-advertised by default); document the lack of an opt-in re-sharing path as an explicit, deliberate v1 boundary in `replication.py`'s module docstring (a future extension point, not a gap to silently leave undocumented).
- [X] T039 [P] [US4] Test in `tests/n2n/test_replication_provenance.py`: a replicated collection's `documents` rows carry correct provenance (source peer, source collection id, timestamp) and are excluded from `build_entries()`'s output when the receiver's own card is built for a third peer.
- [X] T040 [P] [US4] Test in `tests/n2n/test_replication_provenance.py`: deleting a replica removes all its chunks from Chroma and all its rows from the registry; it no longer appears in `rag_list()` (T036) or the card.
- [X] T041 [P] [US4] Test in `tests/n2n/test_replication_provenance.py` (FR-009 second clause): with a replica already present at claw B (sourced from A), a third peer C calls `n2n/knowledge/replicate_manifest` directly against B naming the replica's `collection_id` — assert B refuses it with the same "not found" shape a nonexistent collection gets (no existence oracle), since the T012 filter means the replica was never in B's advertised set for C to have legitimately learned that id from. This closes `/speckit.analyze` finding U2 — the previous coverage only tested non-advertisement, not a direct-request bypass attempt.

**Checkpoint**: US4 independently demonstrable — provenance, isolation, non-propagation, and cleanup all hold, including against a direct-request bypass attempt.

---

## Phase 7: Polish & Cross-Cutting

- [X] T042 [P] Update `workspace/skills/n2n-federation/SKILL.md` with replication trigger/status/re-sync/delete guidance, explicitly distinguishing it from existing query-retrieval delegation guidance.
- [X] T043 [P] Update the NCFED draft's capability-card section in `docs/ietf/draft-capobianco-ncfed-00.md` to note the card's new `embedding_model` field, staged for the **-01** revision — do not alter the live -00 submission (mirrors 064's equivalent task).
- [X] T044 [P] Update `README.md` with a short description of the replication capability (what it does, the `knowledge_replica` grant, the three new `n2n_replicate*` tools) — Constitution Principle XI (`/speckit.analyze` finding C1).
- [X] T045 [P] Update `SOUL.md` with a capability summary for replication, consistent with how feature 064's knowledge-query capability is already summarized there — Constitution Principle XI (C1).
- [X] T046 [P] Update `TOOLS.md` with the infrastructure reference entry for `n2n_replicate`/`n2n_replicate_resync`/`n2n_replicate_delete` — Constitution Principle XI (C1).
- [X] T047 [P] Add a replication-job status node/panel to `ui/netclaw-visual/` (the Three.js HUD) — job state (queued/in-progress/complete/failed), chunk progress, and source/target peer, consistent with how other async operations are already surfaced there — Constitution Principles X and XI (C1).
- [X] T048 Run the full n2n suite (`python3 -m pytest tests/n2n -q`) and confirm zero regressions; map passing tests to SC-001…SC-008.
- [ ] T049 [P] Run the `quickstart.md` manual walkthrough on the live mesh end-to-end (steps 1–11) and record the result.
- [ ] T050 [P] Restart the live mesh/member services to deploy, then confirm a real peer's card shows `embedding_model` and a real replication (and re-sync) completes against a live corpus.

---

## Dependencies & Execution Order

- **Setup (T001–T003)** → **Foundational (T004–T011)** blocks everything below.
- **US1 (T012–T013)** depends on Foundational; independent of US2/US3/US4.
- **US2 (T014–T030)** depends on Foundational; does not require US1's card field to function, but US1 is what lets an operator check compatibility before granting/triggering — deploy US1 first in practice even though it is not a hard code dependency.
- **US3 (T031–T035)** depends on US2 (re-sync reuses `start`'s checks and the identity from T019).
- **US4 (T036–T041)** depends on US2 (needs replicated rows to exist) for T039–T041's tests, and its T038 filter check depends on T012.
- **Polish (T042–T050)** last.

**MVP** = Setup + Foundational + **US1** + **US2** (compatibility is discoverable, and a granted peer can actually replicate a collection asynchronously, retry-safely, with no re-embedding).
Full value = + **US3** (replicas stay current) + **US4** (provenance/cleanup/non-propagation, production-safe).

## Parallel Opportunities

- T002 ∥ T003 (Setup).
- T005 ∥ T006 ∥ T007 ∥ T009 ∥ T011 (Foundational, different files/regions); T004/T008/T010 are sequential prerequisites for later tasks in their own files.
- Within US2: T022/T023/T024/T025/T026/T027/T028/T029/T030 in parallel once T014–T021 land.
- Within US3: T033/T034/T035 in parallel once T031–T032 land.
- Within US4: T039/T040/T041 in parallel once T036–T038 land.
- Polish: T042 ∥ T043 ∥ T044 ∥ T045 ∥ T046 ∥ T047 ∥ T049 ∥ T050; T048 after all code tasks.

## Parallel Example: User Story 2

```bash
# Once T014–T021 land, launch all of these together:
Task: "Add n2n_replicate MCP tool in mcp-servers/n2n-mcp/server.py"
Task: "Update n2n_grant docstring for target_type='knowledge_replica'"
Task: "Test tier-0/grant-type isolation + grant/revoke audit in tests/n2n/test_replication_manifest_batch.py"
Task: "Test mismatch/over-cap refusal in tests/n2n/test_replication_manifest_batch.py"
Task: "Test async job status/progress + failure atomicity in tests/n2n/test_replication_lifecycle.py"
Task: "Test cross-peer replica identity in tests/n2n/test_replication_identity.py"
Task: "Test zero embedder invocations (SC-001) in tests/n2n/test_replication_lifecycle.py"
Task: "Test multi-batch success count-match (SC-004) in tests/n2n/test_replication_lifecycle.py"
Task: "Test single-batch retry idempotency (FR-005) in tests/n2n/test_replication_manifest_batch.py"
```

## Implementation Strategy

### MVP First (US1 + US2)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks everything)
3. Complete Phase 3: US1 (card compatibility discovery)
4. Complete Phase 4: US2 (actual replication)
5. **STOP and VALIDATE**: run the quickstart steps 1–9 (through the mismatch/cap refusals)
6. Deploy/demo if ready — this alone delivers the user's original ask ("replicate my book
   without revectorizing")

### Incremental Delivery

1. Setup + Foundational → foundation ready
2. US1 → US2 → test independently → deploy/demo (MVP!)
3. Add US3 (re-sync) → test independently → deploy/demo
4. Add US4 (provenance/cleanup/non-propagation) → test independently → deploy/demo
5. Each story adds value without breaking previous stories

## Notes

- [P] tasks touch different files (or clearly separable regions of the same file) with no unmet dependency.
- [Story] label maps a task to its user story for traceability — every task inside a user-story phase now carries one (fixed post-`/speckit.analyze`, finding F1).
- Commit after each task or logical group.
- Stop at any checkpoint to validate a story independently.
- Avoid: skipping T021's local-vs-remote task-status distinction — without it, a replication
  job's status check will incorrectly try to poll the source peer for a task it never runs.
- Avoid: writing replication batches with `ChromaStore.add_chunks()` instead of the new
  `upsert_chunks()` (T007) — `add()` errors/duplicates on a retried page; only `upsert()`
  satisfies FR-005's idempotency requirement (T030 tests this explicitly).
