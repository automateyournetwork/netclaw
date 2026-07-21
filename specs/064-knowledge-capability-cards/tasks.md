# Tasks: Knowledge Capability Cards & Knowledge-Aware Routing

**Input**: Design documents from `/specs/064-knowledge-capability-cards/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Included — the spec's Success Criteria and quickstart.md call for pytest coverage,
and the repo is test-driven (`tests/n2n/`).

**Organization**: By user story (US1/US2 = P1, US3 = P2), each independently testable.

## Path Conventions

Single project, in-repo. Federation code: `mcp-servers/protocol-mcp/bgp/federation/`.
Tests: `tests/n2n/`. Skill docs: `workspace/skills/`. Draft: `docs/ietf/`.

---

## Phase 1: Setup

- [X] T001 Confirm the feature-062 RAG surface is callable from the daemon env: `rag_list` (registry) and `rag_search` (retrieval) resolve and return expected shapes; note the exact call path (direct import vs. MCP stdio) to use from `bgp/federation/` in `specs/064-knowledge-capability-cards/research.md` (append a "D7 — RAG call path" note).
- [X] T002 [P] Create empty test modules `tests/n2n/test_knowledge_cards.py` and `tests/n2n/test_knowledge_routing.py` with the shared fixtures import (`conftest.py` manager fixture) so later test tasks just add cases.

---

## Phase 2: Foundational (blocking prerequisites)

**Purpose**: The content-free knowledge-entry builder that US1 advertises and US2/US3 depend on.

- [X] T003 Create `mcp-servers/protocol-mcp/bgp/federation/knowledge.py` with a `build_entries()` that reads the RAG registry (via the T001 path) and returns one content-free entry per **ready** collection (`collection_id`=`knowledge:<collection>`, `name`, `description` from titles/topics, `tags` from distinct `doc_type`, `doc_count`/`page_count`/`chunk_count`, `retrieval`=`n2n/knowledge/query`) per `data-model.md`. Never reads `source_path`/`content_hash`/`capture_*`. (New module also hosts eN2N selection — T013/T014.)
- [X] T004 Extend `_assert_no_secrets` in `mcp-servers/protocol-mcp/bgp/federation/inventory.py` to also scan the `knowledge` array (reject any chunk text / path / hash / secret), so the invariant covers the new surface.
- [X] T005 [P] Add a `topic-only` description mode toggle (env `N2N_KNOWLEDGE_TOPIC_ONLY`, default off) in `knowledge.build_entries()` so titles can be suppressed without hiding the collection (research D5); default advertises titles.

**Checkpoint**: Builder produces correct content-free entries and the no-secrets invariant covers them (unit-testable without a live peer).

---

## Phase 3: User Story 1 — Advertise the knowledge base as an A2A skill (Priority: P1)

**Goal**: A peer pulling the card sees one content-free knowledge entry per authorized collection.
**Independent test**: Ingest a doc, pull the card as a peer, confirm the collection is listed with counts and no content; hidden-for-peer filtering works.

- [X] T006 [US1] Wire `knowledge.build_entries()` into `InventoryBuilder.build` in `mcp-servers/protocol-mcp/bgp/federation/inventory.py`: add a `knowledge` array to the card (sibling of `skills`/`mcp_servers`), advertised **by default** (FR-003), filtered by the existing per-peer `_visibility` on `("knowledge", collection, peer_identity)`.
- [X] T007 [US1] Extend the visibility mechanism (`n2n_set_visibility` path) to accept a `knowledge` kind so an operator can hide a collection from a given peer; confirm hidden collections drop from that peer's card only.
- [X] T008 [P] [US1] Test in `tests/n2n/test_knowledge_cards.py`: card lists one entry per ready collection with correct counts; a claw with zero ready docs emits no `knowledge` entries (absence, not empty).
- [X] T009 [P] [US1] Test in `tests/n2n/test_knowledge_cards.py`: the card contains no chunk text, no `source_path`, no `content_hash`; `_assert_no_secrets` passes with knowledge present and fails if a secret is injected.
- [X] T010 [P] [US1] Test in `tests/n2n/test_knowledge_cards.py`: per-peer visibility — hidden collection absent for peer X, present for peer Y; topic-only mode omits titles but keeps counts/tags.
- [X] T010a [P] [US1] Test in `tests/n2n/test_knowledge_cards.py` (SC-005): the serialized `knowledge` entry size is ~constant as document/chunk counts grow — build a card for a collection with N docs and 10×N docs and assert the entry byte size does not scale with corpus size.

**Checkpoint**: US1 independently demonstrable — card advertisement complete and secret-safe.

---

## Phase 4: User Story 2 — Knowledge-aware routing / delegation (Priority: P1)

**Goal**: A claw delegates a knowledge query to the peer whose corpus is authoritative and returns its cited answer.
**Independent test**: On claw A with no local corpus on T but peer B advertising one, ask A about T → A routes to B, returns B's cited answer, does not fabricate.

- [X] T011 [US2] Implement the **dedicated NCFED method** `n2n/knowledge/query` handler in `mcp-servers/protocol-mcp/bgp/federation/invocation.py` and register it in the service handler map (alongside `n2n/tasks/*`, NOT via the MCP `tools/call` proxy — finding H1): accept `{collection_id, query, k}`, run `rag_search` against the **live** local RAG, and return `{answer, provenance:{peer, collection_id, citations}}` per `contracts/knowledge-card-and-retrieval.md`.
- [X] T012 [US2] Compose the retrieval answer via a local **agent turn** (`gateway.run_agent_turn` fed the `rag_search` hits) so the result is a grounded, cited answer (not raw chunks; FR-008), in `mcp-servers/protocol-mcp/bgp/federation/invocation.py`/`gateway.py`.
- [X] T013 [US2] Implement eN2N knowledge selection in **`mcp-servers/protocol-mcp/bgp/federation/knowledge.py`** (NOT `router.py` — finding H2): embed the query with the RAG embedder, compute cosine similarity against all visible advertised collection descriptions (local + federated peers' cached cards in `service.peer_caps`), pick the highest, deterministic tiebreak by ascending peer identity then `collection_id`; return a Knowledge Route Decision (`target`, `peer_identity`, `collection_id`, `score`, `rationale`) per `data-model.md`.
- [X] T014 [US2] Implement threshold + fallback in `knowledge.py`: a collection matches only at score ≥ `N2N_KNOWLEDGE_MATCH_THRESHOLD` (default 0.5); fallback order **peer → local → model**; MUST NOT emit `peer`/`collection_id` when nothing clears the threshold (no fabricated source, FR-006).
- [X] T015 [US2] Add delegation guidance to `workspace/skills/n2n-federation/SKILL.md`: before answering a document/factual question, consult peers' advertised knowledge and route to the authoritative collection via `n2n/knowledge/query`; state the peer→local→model fallback and the "never invent a federated source" rule.
- [X] T016 [P] [US2] Test in `tests/n2n/test_knowledge_routing.py`: deterministic cosine selection — same query + same advertised set → same collection (stub the embedder for fixed vectors); tiebreak applied and recorded in `rationale`.
- [X] T017 [P] [US2] Test in `tests/n2n/test_knowledge_routing.py`: peer-collection above threshold → decision targets that peer/collection; nothing above threshold → `target=model`, no `peer_identity`/`collection_id`.
- [X] T018 [P] [US2] Test in `tests/n2n/test_knowledge_routing.py`: `n2n/knowledge/query` against a granted, possession-tier peer returns an agent-composed answer with provenance and citations (stub `rag_search` + agent turn).

**Checkpoint**: US2 independently demonstrable — the Byrn book round-trip now happens by deliberate routing.

---

## Phase 5: User Story 3 — Provenance, privacy, and consent (Priority: P2)

**Goal**: Federated knowledge respects visibility, per-peer authorization, admission tier, and audit.
**Independent test**: unauthorized/ hidden-corpus/ restricted-tier attempts are all refused and audited; successful retrieval is audited with corpus + GAIT.

- [X] T019 [US3] Extend the **T011 handler** in `mcp-servers/protocol-mcp/bgp/federation/invocation.py` (edit it in place, not a parallel path — finding L1) to enforce default-deny + possession tier on `n2n/knowledge/query`: reuse `negotiate.allows` so a self-asserted (keyless) peer is denied, and require a per-peer grant for the collection (default-deny), reusing the authorizer path used by `tools/call`/`tasks/submit`. The grant is the Principle-XIV control point (FR-007).
- [X] T020 [US3] No existence oracle: an unknown or not-visible `collection_id` MUST be answered exactly as "no such collection" (same shape as a missing one), in `mcp-servers/protocol-mcp/bgp/federation/invocation.py`.
- [X] T021 [US3] Emit one audit record per retrieval in `invocation.py` via the existing `Auditor`: `{direction=inbound, peer_identity, target_type="knowledge", target_name=collection_id, decision, outcome, channel_kind, gait_ref}` (FR-007).
- [X] T022 [P] [US3] Test in `tests/n2n/test_knowledge_routing.py`: self-asserted (tier-0) peer denied retrieval but may still see authorized knowledge advertisements; possession-tier peer without a grant denied (default-deny); both audited.
- [X] T023 [P] [US3] Test in `tests/n2n/test_knowledge_routing.py`: hidden/unknown `collection_id` returns the missing-collection shape (no existence leak); successful retrieval produces exactly one audit record with collection + GAIT reference.

**Checkpoint**: US3 independently demonstrable — sovereignty/audit guarantees hold under adversarial peers.

---

## Phase 6: Polish & Cross-Cutting

- [X] T024 [P] Update the NCFED draft §11 (Capability Cards) in `docs/ietf/draft-capobianco-ncfed-00.md` to document the `knowledge` skill shape as part of the A2A card mapping, staged for the **-01** revision (FR-010) — do NOT re-render/alter the live -00 submission.
- [ ] T025 [P] Run the quickstart.md manual walkthrough on the live mesh (ingest → advertise → route → answer with citations → visibility → fallback) and record the result; correlate mesh audit + RAG retrieval_log as in the Byrn demo.
- [X] T026 Run the full n2n suite (`python3 -m pytest tests/n2n -q`) and confirm zero regressions; map passing tests to SC-001…SC-005.
- [ ] T027 [P] Restart the live services (`systemctl --user restart netclaw-mesh.service` + members) to deploy, then confirm a real peer sees the `knowledge` array and a routed query answers with provenance.

---

## Dependencies & Execution Order

- **Setup (T001–T002)** → **Foundational (T003–T005)** blocks everything.
- **US1 (T006–T010)** depends on Foundational; is the discovery layer US2 routes against.
- **US2 (T011–T018)** depends on US1 (needs advertised corpora to route to).
- **US3 (T019–T023)** hardens US2's retrieval handler; depends on T011.
- **Polish (T024–T027)** last.

**MVP** = Setup + Foundational + **US1** (a claw's knowledge is discoverable on the card).
Full value = + **US2** (deliberate distributed-RAG routing). **US3** makes it production-safe.

## Parallel Opportunities

- T002 ∥ T001-note; T005 ∥ T003/T004 review.
- Within US1: T008/T009/T010/T010a in parallel (all in one test file, independent cases).
- Within US2: T016/T017/T018 in parallel after T011–T014.
- Within US3: T022/T023 in parallel after T019–T021.
- Polish: T024 (draft) ∥ T025 (walkthrough) ∥ T027 (deploy check); T026 after code tasks.
