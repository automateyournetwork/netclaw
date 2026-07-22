# Phase 0 Research: Chroma-to-Chroma Vector Replication over eN2N

No `NEEDS CLARIFICATION` markers remain in the spec (resolved during `/speckit.specify` and
`/speckit.clarify`). This document records the implementation-approach decisions needed to
turn the clarified spec into a design, each grounded in what already exists in the codebase
rather than new machinery.

## D1: How should the asynchronous replication job (FR-015) be implemented?

- **Decision**: Reuse `bgp/federation/tasks.py`'s `TaskManager` and `delegated_task` table
  exactly as they exist today (feature 053) — no changes to that module.
- **Rationale**: `TaskManager` already provides everything FR-015 asks for: `create()` persists
  a job row and returns an id immediately, `run()` spawns a background `asyncio` worker that
  reports `progress` via a callback, `status()`/`result()` are independent short calls, rows
  survive a daemon restart (its own docstring: "a completed result survives a channel
  drop/reconnect and a daemon restart"), and a retention sweep discards old rows. This is
  precisely the "Replication Job" entity the spec describes. The worker callable for a
  replication job performs the manifest fetch, compatibility/size checks, and the batch pull
  loop (D3), calling `progress(f"{n}/{total} chunks")` between batches.
- **Alternatives considered**: A bespoke replication-job table/queue was considered and
  rejected — it would duplicate `delegated_task` for no benefit; the existing table's columns
  (`direction`, `peer_identity`, `target_type`, `target_name`, `state`, `progress`) already fit.

## D2: What wire methods does replication need?

- **Decision**: Two new low-level methods, mirroring the existing `n2n/knowledge/query`
  request/response pair exactly (`handle_knowledge_query` / `query_remote_knowledge` in
  `invocation.py`): `n2n/knowledge/replicate_manifest` (returns `embedding_model` and total
  `chunk_count` for a collection) and `n2n/knowledge/replicate_batch` (returns one page of
  `{id, embedding, text, metadata}` given an `offset`/`limit`). No new method *family* —
  `n2n/tasks/submit|status|result|cancel` is not reused for the wire calls themselves (the job
  is local to the receiver, per D1); it is reused only as the pattern for the job wrapper.
- **Rationale**: The receiver already knows how to drive a sequence of small, independent
  `ch.call()`s to a peer (that's exactly what `query_remote_knowledge` does once). Paginating
  that same call is the smallest change that satisfies FR-005's batching requirement, and it
  keeps flow control simple: the receiver only pulls as fast as it can verify and write
  locally, with no new push-from-source machinery needed on the sending side.
- **Alternatives considered**: Push-based transfer (source proactively streams batches to the
  receiver) was rejected — it would require the source to open new outbound calls mid-transfer,
  a direction the existing channel handlers don't do today; pull-based needs no new capability
  on the sending side beyond two more request handlers of the same shape as `knowledge/query`.

## D3: How is authorization for replication kept distinct from query-retrieval (FR-002)?

- **Decision**: A new `target_type="knowledge_replica"` value passed to the existing
  `Authorizer.grant()`/`authorize()`/`revoke()` methods in `authorization.py`, alongside the
  existing `target_type="knowledge"` used for query-retrieval. Both handlers
  (`handle_knowledge_query`, and the two new replication handlers) call
  `self.authz.authorize(peer, <their own target_type>, collection_id)` — a grant for one
  `target_type` has no effect on the other, satisfying FR-002 with zero schema change (the
  `invocation_grant` table's `target_type` column already accepts arbitrary strings).
- **Rationale**: `authorization.py`'s grant model was already designed to be
  target-type-generic; adding a second target type for the same `collection_id` is exactly its
  intended extension point, not a workaround.
- **Alternatives considered**: A boolean "replication-allowed" flag on the existing knowledge
  grant row was rejected — it would make replication opt-out-by-widening an existing
  query-only grant rather than opt-in, the opposite of what FR-002 requires.

## D4: How is replication gated at the trust-tier level?

- **Decision**: Add `"knowledge/replicate"` to `negotiate.py`'s `TIER0_DENIED` frozenset,
  alongside the existing `"knowledge/query"` entry. A self-asserted (keyless) peer cannot
  invoke either manifest or batch handlers, exactly like query-retrieval.
- **Rationale**: Replication is at least as sensitive as query-retrieval (it moves the
  underlying data, not just an answer); reusing the identical tier gate keeps the two
  consistent and is a one-line addition to an existing, already-audited list.

## D5: Where does a replica's embedding-model advertisement (FR-001) come from?

- **Decision**: The currently configured `RAG_EMBEDDING_MODEL` (rag-mcp `config.EMBEDDING_MODEL`,
  default `BAAI/bge-small-en-v1.5`) is advertised as the collection's `embedding_model` on the
  card — the same value rag-mcp itself uses for every local embed/query call today.
- **Rationale/limitation**: rag-mcp does not currently record, per document or per collection,
  which model actually produced its stored vectors — it is a single global setting for the
  whole instance. Advertising the current global setting is accurate for the common case (an
  operator does not change embedding models on a live instance) and is consistent with how
  local retrieval already implicitly trusts this setting for every query. If an operator did
  change `RAG_EMBEDDING_MODEL` after a collection was originally ingested, the advertised value
  could be wrong for that older data — a pre-existing latent inconsistency in feature 062, not
  something this feature can retroactively fix. Per-document embedding-model tracking is a
  reasonable follow-up but is out of scope here (the spec's edge case on this explicitly limits
  compatibility checking to an opaque model-identifier string).

## D6: How does a replica get a stable, collision-free local identity (FR-016)?

- **Decision**: A replica's local Chroma collection name and its `documents.collection` value
  are both deterministically derived as `replica__<source_peer_identity>__<source_collection_id>`
  — never the bare source `collection_id`. This name is stable across re-syncs (D7).
- **Rationale**: Peer identity is already the federation's own unique namespace (every peer has
  exactly one identity in `federation.db`); combining it with the source's `collection_id`
  (unique only within that one peer) yields a value that is unique across the whole mesh by
  construction, satisfying FR-016 without a lookup table.

## D7: How does a full-replace re-sync (FR-010) stay atomic without a new store?

- **Decision**: Reuse rag-mcp's existing ingest atomicity idiom — `registry.new_document()`
  inserts a `pending` row (here, `kind='replica'`), the batch pull writes into the target Chroma
  collection, and `registry.finalize()` flips it to `ready` in one transaction, exactly as local
  document ingestion already does. For a **re-sync** specifically: batches are written into a
  freshly created, temporarily-named staging Chroma collection first; once the manifest count is
  verified, the previous live collection (same stable name as D6) is deleted and the staging
  collection is renamed to that stable name (`Collection.modify(name=...)`, an existing Chroma
  API), and the old `documents` rows for this replica are replaced by the new ones in the same
  local transaction. An initial (non-re-sync) replication skips the extra staging step and
  writes directly under the stable name, since there is no prior version to protect.
- **Rationale**: This is the same "observe → verify → flip" shape the constitution already
  requires for device changes (Principle VIII) and that feature 062 already uses for ingestion;
  no new persistence concept is introduced. The brief window between deleting the old collection
  and renaming staging into place is an accepted, documented tradeoff (an operator-triggered,
  infrequent admin action, not a high-concurrency path) rather than a spec requirement to solve
  with e.g. distributed transactions.
- **Alternatives considered**: Versioned collection names with a separate "current pointer"
  table were considered and rejected as unnecessary — they would solve a concurrency problem
  this feature does not have (single local writer, operator-triggered), at the cost of a new
  table this plan otherwise avoids.

## D8: Where does per-chunk document context (title, page) come from without a separate manifest breakdown?

- **Decision**: The manifest (D2) carries only collection-level totals (`embedding_model`,
  `chunk_count`); no per-document breakdown is transferred separately. Each chunk's own
  metadata (already required by FR-004: document title, chunk ordinal, breadcrumbs, document
  id) is what the receiver uses to reconstruct one local `documents` row per distinct source
  document id once the full batch stream has been received and verified.
- **Rationale**: This avoids a second, redundant wire shape carrying the same information the
  chunk metadata already carries, and matches the spec's explicit non-goal of partial/selective
  per-document replication — the unit of transfer is the whole collection, so a document
  breakdown is a derived, receiver-side aggregation step, not new data on the wire.

## D9: How is the size cap (FR-017) enforced without a new config surface?

- **Decision**: A new env var, `N2N_REPLICATION_MAX_CHUNKS` (conservative default, e.g. in the
  low tens of thousands), read by `replication.py` and checked against the manifest's
  `chunk_count` before any batch is requested.
- **Rationale**: Matches the existing pattern of operator-tunable ceilings already used by
  feature 062 (`RAG_MAX_DOC_MB`, `RAG_MAX_DOC_PAGES` in `config.py`) — a new, single,
  purpose-specific env var rather than overloading an unrelated existing one.

## D11: How is batch-retry idempotency (FR-005) actually satisfied?

- **Decision**: Replication writes use a new `ChromaStore.upsert_chunks()` (keyed by chunk
  `id`, via Chroma's `Collection.upsert()`), not the existing `add_chunks()` (`Collection.add()`).
- **Rationale**: `add()` is correct for local ingestion, where a duplicate id is a real bug
  worth surfacing as an error. Replication is different: a single batch call can legitimately
  be retried mid-job (one page's response is lost or times out) without the whole job
  restarting, and FR-005 requires that retry to be a no-op, not an error or a duplicate.
  `upsert()` (same ids, same content, applied twice) satisfies that directly with no additional
  bookkeeping (no need to pre-check which ids already exist).
- **Alternatives considered**: Checking existing ids before every `add()` call was rejected as
  more code for the same outcome `upsert()` already gives for free.

## D12: How is grant/revoke administrative action audited (FR-012)?

- **Decision**: Add `audit.record()` calls directly to the daemon's `/n2n/grants` POST and
  DELETE handlers in `bgp-daemon-v2.py` (`direction="local"`, `target_type=<the granted
  target_type>`, `target_name=<target_name>`, `decision="granted"`/`"revoked"`), rather than
  inside `Authorizer.grant()`/`revoke()` themselves.
- **Rationale**: Verified directly against the running code — neither `Authorizer.grant()`/
  `revoke()` nor the daemon routes that call them write any audit record today, for *any*
  target_type, not just the new `knowledge_replica` one (found during `/speckit.analyze`).
  FR-012 requires grant/revocation audit for replication; the smallest correct fix is generic
  (audit every grant/revoke, not a `knowledge_replica`-only special case), since a
  target-type-specific audit hook would be inconsistent with how every other grant already
  behaves and would leave the pre-existing gap for `"tool"`/`"skill"`/`"knowledge"` grants
  unaddressed right next to the new code that fixes it only for one type.
- **Alternatives considered**: Auditing only `knowledge_replica` grants (narrower, matches this
  spec's letter) was rejected as leaving an inconsistent, confusing audit trail (some grant
  types audited, others not, with no principled reason why) for a two-line fix that closes the
  gap everywhere.
