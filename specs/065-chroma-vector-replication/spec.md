# Feature Specification: Chroma-to-Chroma Vector Replication over eN2N

**Feature Branch**: `065-chroma-vector-replication`
**Created**: 2026-07-22
**Status**: Draft
**Input**: User description: "Chroma-to-chroma vector replication over eN2N: let one claw replicate a peer's RAG collection (e.g. a book) by transferring the already-computed embeddings, chunk text, and metadata directly into its own local ChromaDB store, instead of re-embedding the source documents locally."

## Overview

Feature 064 made a claw's local RAG collections (feature 062) discoverable to federated
peers — a capability card entry per collection, and a `n2n/knowledge/query` method that lets
a peer ask a question and get back a grounded, cited answer without any content ever leaving
the owning claw. 064 deliberately reserved **replication** as out of scope, because pushing
raw vectors and text across the wire is a different governance model from federated query:
the data leaves, revocation becomes best-effort, and embedding vectors carry real inversion
risk if the receiving side treats them as sole knowledge (064 §Assumptions).

This feature is that reserved follow-on. It lets an operator explicitly and consensually copy
a peer's already-embedded RAG collection — e.g. a book — into their own local Chroma store, so
the receiving claw can answer queries about it locally, offline, without a federated round trip
and **without re-running the embedding model** over the source documents (embeddings, chunk
text, and metadata are transferred as-is and written directly via the receiver's own
`ChromaStore.add_chunks()`). This only produces a correct vector space if both claws embedded
with the same model — 064's card does not currently say what model a collection was embedded
with, so this feature also extends the knowledge advertisement with that fact, and treats a
mismatch as a hard, pre-transfer refusal rather than a silent re-embed.

Because replication moves real content (not just metadata), it requires its own explicit,
per-collection consent — separate from and in addition to 064's query-retrieval grant — and
every replica must be visibly marked as a copy, not conflated with locally-authored knowledge.

## Clarifications

### Session 2026-07-22

- Q: What should replication deliver in v1 — a one-shot push, continuous subscription, or
  something in between? → A: A one-shot snapshot push of a full collection, plus a manual
  re-sync the operator can trigger later when the source changes. No automatic/continuous
  subscription in this feature.
- Q: How should an embedding-model mismatch between source and receiver be handled? → A: Reject
  up front with a clear error naming both models. No silent re-embedding, no partial import,
  no operator override in v1.
- Q: When an operator triggers replication (or a re-sync) of a book-sized collection, does the
  request block until the transfer completes, or return immediately? → A: Asynchronous — the
  trigger call returns immediately with a job reference; the operator checks status or is
  notified when the transfer finishes.
- Q: How should a replica's local identity be determined so replicas from different source
  peers can never collide? → A: Always derived from source peer + source collection_id
  (namespaced by peer), since `collection_id` is only unique within one claw.
- Q: Should this feature enforce a maximum collection size a single replication may transfer?
  → A: Yes — a configurable maximum (chunk count and/or size) with a sane default, consistent
  with existing RAG ingestion caps; a collection exceeding it is refused up front.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Discover whether a peer's collection is safe to replicate (Priority: P1)

Before requesting a copy of anything, an operator (or their claw, acting on the operator's
behalf) needs to know which embedding model produced a peer's advertised collection, so they
can tell up front whether replication would even produce a usable local copy. Today's
capability card (064) says what a collection is about but not how it was embedded.

**Why this priority**: Compatibility must be checkable before anyone asks for a transfer.
Without this, every replication attempt would have to fail after starting, which is exactly
the "partial import" outcome this feature is designed to avoid.

**Independent Test**: Ingest a document into a local RAG collection, fetch the card as a peer,
and confirm the knowledge entry names the embedding model used — with no chunk text, vectors,
or other content present (still content-free, consistent with 064's `_assert_no_secrets`
invariant).

**Acceptance Scenarios**:

1. **Given** a claw with a RAG collection embedded with model M, **When** a federated peer
   fetches its capability card, **Then** the collection's knowledge entry names M alongside its
   existing topic/description/counts.
2. **Given** the same card, **When** it is built, **Then** it still contains no chunk text, no
   vectors, no source paths, and passes the existing content-free check.

---

### User Story 2 - Consented one-shot replication of a collection (Priority: P1)

An operator whose claw has been granted replication consent for a specific peer collection
(distinct from, and in addition to, the query-only grant from 064) triggers a one-time copy.
The source claw sends every chunk's embedding, text, and safe metadata; the receiving claw
writes them directly into its own local Chroma store — no LLM involvement, no re-embedding —
and the collection becomes locally queryable once, and only once, the full transfer is
verified complete.

**Why this priority**: This is the payoff the user asked for — turning a federated query
relationship into a local, offline-capable copy without paying to re-embed a whole book.

**Independent Test**: Grant replication consent for a multi-hundred-chunk test collection
between two claws with matching embedders, trigger replication, and confirm the receiver's
local collection returns correct query results with zero embedder invocations recorded during
import.

**Acceptance Scenarios**:

1. **Given** a source claw with a collection and a matching-embedder peer holding a replication
   grant for that collection, **When** the peer triggers replication, **Then** every chunk's
   id, embedding, text, and safe metadata arrives at the receiver and is written via the
   receiver's own local vector store — not re-embedded.
2. **Given** the same setup but the peer holds only 064's query-retrieval grant (not a
   replication grant), **When** replication is attempted, **Then** it is refused and audited;
   query-retrieval continues to work unaffected.
3. **Given** a source collection embedded with model M and a receiver configured for model N ≠
   M, **When** replication is attempted, **Then** it is refused before any vector data is sent,
   with an error naming both M and N.
4. **Given** a transfer that is interrupted partway (e.g. connection drop), **When** the
   receiver checks the collection afterward, **Then** the partial data is not queryable — the
   collection either completes fully on retry or is discarded, never left half-populated.
5. **Given** a triggered replication, **When** the operator's trigger request returns, **Then**
   it returns immediately with a job reference rather than blocking until the transfer
   finishes; the operator can check that job's status (queued/in-progress/complete/failed, with
   chunk progress) at any time and is able to learn when it finishes without having kept the
   original request open.

---

### User Story 3 - Manual re-sync when the source changes (Priority: P2)

Some time after an initial replication, the source collection gains new documents or edits.
The operator who received the original copy triggers a manual re-sync, which re-checks consent
and compatibility and replaces the existing replica's contents with the current source
snapshot — no duplicate or stale chunks left behind.

**Why this priority**: A one-shot copy that can never be refreshed becomes stale and
untrustworthy the moment the source changes. This is the minimum viable "keep it current"
story without building a full continuous-sync subsystem.

**Independent Test**: Replicate a collection, add a document to the source, trigger a manual
re-sync, and confirm the receiver's local copy now includes the new document's chunks with no
duplicates of the unchanged chunks.

**Acceptance Scenarios**:

1. **Given** a previously replicated collection whose source has since changed, **When** the
   operator triggers a re-sync, **Then** the local replica is replaced with the current source
   snapshot (added chunks appear, removed chunks disappear, unchanged chunks are not
   duplicated).
2. **Given** the same re-sync, **When** consent has been revoked in the meantime, **Then** the
   re-sync is refused and audited; the existing (now-stale) local replica is left in place
   untouched — revocation does not reach back and delete it.
3. **Given** a triggered re-sync, **When** the operator's trigger request returns, **Then** it
   returns immediately with a job reference, the same as an initial replication (Story 2,
   scenario 5) — the previous replica's contents remain queryable and unchanged until the
   re-sync job completes and the replacement is applied.

---

### User Story 4 - Replica provenance, isolation, and cleanup (Priority: P2)

An operator looking at their local knowledge base needs to be able to tell, at a glance, which
collections they authored locally and which arrived via replication from a peer — including
which peer, which source collection, and when. They also need a way to delete a replica they no
longer want, and replicas must not silently get re-shared onward to other peers as if they were
the receiver's own original knowledge.

**Why this priority**: This is what keeps replication honest about provenance and bounded in
its blast radius — the exact concern 064 raised about revocation being "best-effort" once data
leaves the source. Making replicas visibly distinct and non-propagating is the mitigation.

**Independent Test**: Replicate a collection, list local knowledge collections, confirm the
replica is labeled with its source peer/collection/timestamp and is visually distinct from a
locally-ingested collection; confirm the receiver's own capability card does not re-advertise
the replica to a third peer without an explicit separate opt-in; delete the replica and confirm
it is fully removed.

**Acceptance Scenarios**:

1. **Given** a successfully replicated collection, **When** the operator lists local
   collections, **Then** the replica shows its source peer identity, source collection id, and
   replication timestamp, and is distinguishable from locally-authored collections.
2. **Given** the same replica, **When** the receiver's own capability card is built for a third
   peer, **Then** the replica is not advertised as the receiver's own knowledge unless the
   operator has explicitly opted that specific replica into re-sharing.
3. **Given** a replica the operator no longer wants, **When** they delete it, **Then** all of
   its chunks are removed from local storage and it no longer appears in listings.

### Edge Cases

- What happens when the embedding models match by name but differ by version/fine-tune? Out of
  scope for v1 — the compatibility check compares the advertised model identifier as a single
  opaque string; finer-grained compatibility (dimension check, version pinning) is a reasonable
  future refinement, not required here.
- What happens if the source collection is renamed or deleted between granting consent and the
  transfer running? The transfer is refused with a clear "source collection not found" error;
  an existing local replica from an earlier successful run is left untouched.
- What happens if the receiving claw already has a locally-authored collection with the same
  name as the incoming replica? Replication MUST NOT merge into or overwrite a locally-authored
  collection; the replica is written under its own distinct identity so the two can never be
  confused.
- What happens if two different federated peers each advertise a collection with the same
  `collection_id` (e.g. both use a default name) and the operator replicates from both? Because
  a replica's local identity is always derived from source peer + source collection_id (not the
  bare collection_id alone), the two replicas coexist locally without collision or overwrite.
- What happens to a very large collection (e.g. tens of thousands of chunks)? The transfer is
  split into multiple batches so no single message exceeds the federation channel's framing
  limits; a stalled or failed batch is retried without duplicating already-received chunks.
- What happens if the same replication is triggered twice concurrently? The second attempt is
  refused (or queued) rather than allowed to run in parallel and interleave writes with the
  first.
- What happens when the source operator revokes the replication grant after a replica already
  exists locally? Future replication and re-sync are refused; the existing local replica is
  unaffected (the receiver's own data now, per Story 3's second scenario) — deleting it is a
  separate, explicit action by the receiving operator (Story 4).
- What happens if the operator checks a replication job's status while the transfer is still in
  progress? The status check returns an in-progress state with chunk/batch progress — it is
  never treated as an error, and it never reports success before the manifest-count
  verification (FR-006) has actually passed.
- What happens if a source collection is larger than the receiver's configured maximum size
  (FR-017)? Replication is refused before any batch transfer begins, naming the collection's
  size and the configured limit; the operator (or their configuration) can raise the limit and
  retry, but no partial transfer is attempted.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Each knowledge entry on the capability card (feature 064) MUST additionally
  advertise the **embedding model identifier** used to produce that collection's vectors, so a
  prospective replicator can check compatibility before requesting anything. This remains
  content-free — no vectors, text, or dimensions are required, only the model identifier.
- **FR-002**: Replication of a collection's actual vectors/text/metadata MUST require an
  explicit, per-peer, per-collection consent distinct from — and in addition to — feature 064's
  query-retrieval grant. Holding a query-retrieval grant MUST NOT by itself authorize
  replication.
- **FR-003**: Before any vector data is transferred, the requesting claw's local embedding
  model MUST be compared against the source collection's advertised embedding model (FR-001).
  On any mismatch, the operation MUST be refused before transfer begins, with an error naming
  both models; there MUST be no silent re-embedding, no partial import, and no operator
  override in v1.
- **FR-004**: A successful replication MUST transfer, for every chunk in the source collection,
  its id, embedding vector, chunk text, and safe metadata (document title, chunk ordinal,
  section/page breadcrumbs, document id) exactly as stored at the source.
- **FR-005**: Because a full collection (e.g. a book, thousands of chunks) exceeds what fits in
  a single federation message, the transfer MUST be split into multiple sequential batches,
  transferred one at a time with no batch requested before the prior one is fully processed;
  applying the same batch twice (e.g. after a retry) MUST NOT produce duplicate chunks on the
  receiving side.
- **FR-006**: The receiving claw MUST NOT expose a replicated collection for local querying
  until the transfer is verified complete against a manifest (expected chunk count) sent at the
  start of the transfer; an interrupted or failed transfer MUST leave no partially-queryable
  collection — either the full replica exists or none of it does.
- **FR-007**: Replicated chunks MUST be written into the receiver's own local vector store as a
  mechanical copy (ids, embeddings, text, metadata written as received) with no re-embedding
  and no LLM-generated or LLM-altered content introduced during import.
- **FR-008**: Every replicated collection MUST carry provenance — source peer identity, source
  collection id, and replication timestamp — and MUST be visibly distinguishable from a
  locally-authored collection everywhere collections are listed (including the operator-facing
  knowledge listing and, where applicable, the HUD).
- **FR-009**: A replicated collection MUST NOT itself be re-advertised on the receiver's own
  capability card as the receiver's original knowledge, and MUST NOT be replicated onward to a
  third peer, unless the receiving operator explicitly opts that specific replica into
  re-sharing. This bounds onward propagation of data whose source consent may later be revoked.
- **FR-010**: The operator MUST be able to trigger a manual re-sync of a previously replicated
  collection, which re-runs the consent and compatibility checks (FR-002, FR-003) and replaces
  the existing replica's contents with the current source snapshot — added source chunks
  appear, removed source chunks are removed, unchanged chunks are not duplicated.
- **FR-011**: Revoking a replication consent grant MUST block future replication and re-sync
  requests but MUST NOT retroactively delete an already-completed local replica; deleting a
  replica is a separate, explicit action available to the receiving operator.
- **FR-012**: Every replication attempt, successful transfer, re-sync, consent grant, and
  consent revocation MUST be recorded in the audit trail with peer identity, collection id,
  chunk count, and a GAIT reference, consistent with existing federation audit practice
  (features 057/060/064).
- **FR-013**: Replication MUST be refused if the source collection is not visible to the
  requesting peer under feature 064's existing per-peer visibility rules — a collection must be
  discoverable before it can be replicated.
- **FR-014**: Replication MUST NOT bypass the content-scrubbing that already happens at
  document ingestion (feature 062); it forwards chunks exactly as they exist in the source's
  own local store and performs no independent content inspection beyond the existing
  ingestion-time scrubbing.
- **FR-015**: Triggering a replication or a re-sync MUST be asynchronous: the trigger request
  MUST return immediately with a job reference rather than blocking until the transfer
  finishes. The operator MUST be able to check that job's status (queued, in-progress,
  complete, or failed, including chunk/batch progress) independently of the original trigger
  request, and MUST be able to learn when the job finishes without keeping that request open.
- **FR-016**: A replica's local identity MUST be derived from **both** the source peer identity
  and the source `collection_id` (not the bare `collection_id` alone), so that replicas of
  same-named collections from two different source peers can never collide or overwrite one
  another; re-sync (FR-010) targets this same derived local identity.
- **FR-017**: Replication MUST enforce a configurable maximum on the size of a collection it
  will transfer (by chunk count and/or byte size), with a conservative default, consistent with
  existing RAG ingestion caps. A source collection whose manifest (FR-006) declares a count
  above the receiver's configured maximum MUST be refused before any batch transfer begins,
  with an error stating the collection's size and the configured limit. This cap applies to
  both an initial replication and a re-sync.

### Key Entities *(include if feature involves data)*

- **Replicated Collection (Replica)**: A local vector-store collection populated via
  replication rather than local document ingestion. Its local identity is always derived from
  source peer + source `collection_id` (FR-016), never the bare `collection_id` alone, so
  replicas of same-named collections from different peers never collide. Carries provenance
  (source peer identity, source collection id, replication timestamp, source embedding model)
  and is queryable exactly like a locally-authored collection, but distinguishable in every
  listing.
- **Replication Grant**: An explicit, per-peer, per-source-collection consent record
  authorizing a specific peer to replicate a specific collection. Distinct from feature 064's
  query-retrieval grant; both may exist independently for the same collection.
- **Replication Manifest**: A small descriptor sent before the batch transfer — source
  collection id, embedding model identifier, and expected chunk count — used by the receiver to
  verify a transfer completed fully before exposing the replica for querying.
- **Replication Batch**: One bounded slice of the transfer (a subset of chunk ids, embeddings,
  texts, and metadata) sized to fit within the federation channel's per-message limits;
  batches are applied idempotently so a retried batch does not duplicate chunks.
- **Replication Job**: The asynchronous unit of work created when an operator triggers a
  replication or re-sync. Carries a job reference, a status (queued, in-progress, complete, or
  failed), and chunk/batch progress; exists independently of the request that created it so the
  operator can check on it or be notified of completion without having kept a connection open.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An operator can turn a consented peer collection (including a book-sized corpus of
  thousands of chunks) into a locally queryable copy with zero calls to an embedding model
  during the import itself.
- **SC-002**: 100% of replication attempts between mismatched embedding models are refused
  before any vector data is sent — zero bytes of chunk content or vectors transferred on
  mismatch.
- **SC-003**: 100% of successfully replicated collections are visibly labeled with correct
  source provenance (peer, collection, timestamp) in local listings, and 0% are ever confused
  with or merged into a locally-authored collection of the same name.
- **SC-004**: For a collection whose size exceeds a single federation message, 100% of
  successful replications result in a receiver-side chunk count that exactly matches the source
  manifest's expected count, with no data loss and no duplicate chunks from batch retries.
- **SC-005**: 100% of replication, re-sync, grant, and revocation actions appear in the audit
  trail; unauthorized replication attempts (no grant, wrong grant type, or revoked grant) are
  refused 100% of the time.
- **SC-006**: After a manual re-sync, the local replica's chunk count and contents match the
  current source snapshot exactly — no stale chunks from the prior version remain, and no
  chunks are duplicated.
- **SC-007**: An operator can check the status of any in-flight replication or re-sync job
  (including chunk/batch progress) at any time without waiting for it to finish, and 100% of
  triggering requests return immediately rather than blocking for the duration of the transfer.
- **SC-008**: 100% of replication attempts against a collection larger than the configured
  maximum are refused before any batch transfer begins — zero chunks transferred on an
  over-limit attempt.

## Assumptions

- Feature 064 (knowledge capability cards) is a hard prerequisite: this feature extends its
  card advertisement (adding the embedding-model field) and reuses its per-peer visibility and
  audit conventions rather than introducing a parallel discovery mechanism.
- The card does not currently advertise which embedding model produced a collection — adding
  that field (FR-001) is new work in this feature, not something 064 already provides.
- Feature 062 (rag-mcp) remains the source of truth for local storage on both ends: replication
  writes through the receiver's own existing vector-store write path (the same one local
  ingestion uses), so replicated data behaves identically to local data for query purposes.
- The existing federation wire framing (bounded per-message and per-frame sizes) is reused as-is;
  this feature's batching requirement operates by sending multiple application-level messages,
  not by changing the underlying transport's frame limits.
- Continuous/automatic subscription sync, cross-embedding-model translation (re-embedding to
  reconcile a mismatch), and partial/selective replication of a subset of a collection's chunks
  are all explicitly out of scope for this feature; a future spec may revisit any of them.
- The maximum collection size (FR-017) is operator-configurable with a conservative built-in
  default; the exact default value is a planning-level decision, consistent with how existing
  RAG ingestion caps (e.g. document size/page limits) are already configured in feature 062.
- Content-level scrubbing for secrets/PII already happens once, at document ingestion (feature
  062); this feature does not duplicate that check on the replication path, only enforces that
  replication cannot occur outside of the existing consent, visibility, and audit controls.

## Dependencies

- Feature 064 (knowledge capability cards) — card advertisement to extend, per-peer visibility,
  audit/GAIT conventions, and the existing grant/authorization pattern to extend with a new
  replication-specific grant type.
- Feature 062 (rag-mcp) — local vector store write path, document registry, and embedder
  configuration on both the source and receiving claw.
- Features 057/060 — admission tiers, per-peer authorization, audit/GAIT trail.
- The NCFED federation channel's existing chunked message framing — bounds how a full
  collection's transfer must be batched.
