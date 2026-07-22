# Phase 1 Data Model: Chroma-to-Chroma Vector Replication over eN2N

No new top-level store. This feature extends two existing stores — rag-mcp's `documents`
registry (feature 062) and its Chroma vector store — plus reuses the existing federation
`invocation_grant` and `delegated_task` tables (features 052/053/057) generically. Entities
below are (1) card field additions (wire, read-only extension of 064), (2) registry/storage
extensions (persistent), and (3) in-memory/job entities.

## Entity: Knowledge Skill (card entry) — extended

Sibling of the feature-064 entity of the same name; one new field.

| Field | Type | Source | Notes |
|-------|------|--------|-------|
| `embedding_model` | string | rag-mcp `config.EMBEDDING_MODEL` (currently configured, D5) | NEW (FR-001). Opaque model identifier a prospective replicator compares against its own configuration before requesting anything. Still content-free — no vectors, dimensions, or weights. |

**Invariants**: Unchanged from 064 otherwise — still passes `_assert_no_secrets`; still
absent (not empty) for a claw with zero ready documents; still filtered by per-peer visibility.
A `kind='replica'` row (below) is explicitly excluded from `build_entries()`'s aggregation, so
a replicated collection is never advertised as the receiver's own knowledge by default (FR-009).

## Entity: Document Registry row — extended (`rag-mcp` `documents` table)

Existing feature-062 table (`~/.openclaw/rag/rag.db`). Extended for this feature:

| Change | Detail |
|--------|--------|
| `kind` CHECK constraint | Gains `'replica'` alongside the existing `'document'`, `'snapshot'` (schema_version bump). |
| `source_peer_identity` | NEW nullable column. Set only on `kind='replica'` rows — the federation identity of the peer this row was replicated from. |
| `source_collection_id` | NEW nullable column. The advertised `collection_id` on the *source's* card (e.g. `knowledge:documents`) that this row came from. |
| `source_embedding_model` | NEW nullable column. The `embedding_model` the source advertised at replication time (D5) — recorded for provenance even though compatibility was already verified before transfer. |
| `replicated_at` | NEW nullable column. ISO-8601 timestamp of the (re-)sync that produced this row's current content. |
| `collection` (existing column) | For `kind='replica'` rows, always the stable derived value `replica__<source_peer_identity>__<source_collection_id>` (D6/FR-016) — never the bare source collection name. |

**Invariants**: `kind='replica'` rows follow the same `ingest_status` state machine as
ordinary documents (`pending → ... → ready | error`; only `ready` rows are queryable/listed) —
reusing `registry.new_document()` / `registry.finalize()` as the atomic commit point (D7),
satisfying FR-006 (no partial import) with the same mechanism feature 062 already relies on for
ingestion atomicity. A `kind='replica'` row's `collection` value MUST NEVER equal a
locally-authored (`kind='document'`) row's `collection` value — enforced structurally by the
`replica__` prefix, not by a runtime check, so the two can never collide or be merged (spec
Edge Cases).

## Entity: Chroma Collection — extended (`~/.openclaw/rag/chroma/`)

Existing feature-062 Chroma store. One collection per replica, named identically to the
`documents.collection` value above (`replica__<peer>__<source_collection_id>`), holding the
same chunk shape (`ids`, `embeddings`, `documents` [text], `metadatas`) as any locally-authored
collection — written via the existing `ChromaStore.add_chunks()`, unmodified.

**Lifecycle (re-sync, D7)**: An initial replication writes directly into this stable-named
collection. A re-sync writes into a temporary staging collection first, verifies the manifest
count, deletes the previous stable-named collection, and renames staging into the stable name
(`Collection.modify(name=...)`) — the same "observe → verify → flip" shape as document
ingestion, applied to a whole collection instead of one document.

## Entity: Replication Grant (`invocation_grant` table — reused, new value)

Existing feature-057 table. No schema change — a replication grant is a row with
`target_type="knowledge_replica"` and `target_name=<collection_id>`, distinct from a
query-retrieval grant's `target_type="knowledge"` row for the same `collection_id` (FR-002).
Both may exist independently; `Authorizer.grant()`/`revoke()`/`list_grants()` operate on it
exactly as they do on every other target type today.

## Entity: Replication Manifest (wire, transient)

Returned by `n2n/knowledge/replicate_manifest`. Not persisted as its own row — its fields are
checked against the local embedder/size cap and then discarded (the receiver's own count of
chunks actually received, not this manifest, is what gets persisted).

| Field | Type | Notes |
|-------|------|-------|
| `collection_id` | string | Echo of the requested source collection. |
| `embedding_model` | string | The source's currently configured embedder (must match the requester's own, FR-003). |
| `chunk_count` | int | Total chunks the source will provide; used both for the size-cap check (FR-017) before any batch is requested, and afterward to verify completeness (FR-006). |

## Entity: Replication Batch (wire, transient)

Returned by `n2n/knowledge/replicate_batch` given `{collection_id, offset, limit}`. One page of:

| Field | Type | Notes |
|-------|------|-------|
| `ids` | string[] | Chunk ids, as stored at the source. |
| `embeddings` | float[][] | Raw vectors, unmodified — never recomputed (FR-007). |
| `texts` | string[] | Chunk text, unmodified. |
| `metadatas` | object[] | Safe per-chunk metadata: document title, chunk ordinal, section/page breadcrumbs, source document id (FR-004). Never `source_path`, `content_hash`, or capture commands — the same exclusion 064 already applies to card content, extended here to chunk metadata. |

Applied idempotently by the receiver: writes go through Chroma's **upsert** semantics
(`Collection.upsert()`, keyed by chunk `id`), not `add()` — `add()` errors or duplicates on an
id already present, which a mid-job single-batch retry (as opposed to a whole-job restart)
would trigger. Upserting the same batch twice is a no-op the second time — same ids, same
content, no duplication (FR-005). This is a deliberate deviation from the existing
`ChromaStore.add_chunks()` (which uses `add()`, appropriate for local ingestion where a
duplicate id is a bug, not a possible network retry) — replication's write path uses a
distinct `ChromaStore.upsert_chunks()` for this reason (see `research.md` D11).

## Entity: Replication Job (`delegated_task` table — reused, new target_type)

Existing feature-053 table/class (`TaskManager`), unmodified. A replication or re-sync trigger
calls `TaskManager.create(direction="inbound", target_type="knowledge_replicate",
target_name=<collection_id>, ...)` and `TaskManager.run(task_id, worker)`, where `worker` is
the manifest-fetch → compatibility/size check → batch-pull-loop function (D1/D3).
`direction="inbound"` is deliberate, not a misnomer: it is what makes the daemon's
`/n2n/tasks/<id>` status handler take the plain local-read path instead of its
outbound-task branch, which polls the *peer* for status — a replication job has no peer-side
counterpart to poll, since the pulling happens entirely from our own side (task manifest/batch
calls are outbound `ch.call()`s made *by* the worker, not a task the peer runs for us). Reuses
the existing `state` machine (`submitted → working → completed | failed | cancelled`),
`progress` field (chunk/batch progress, per FR-015), and `status()`/`result()`/`cancel()`
accessors verbatim — no new columns, no new class.

## State / lifecycle summary

1. **Discover** — operator/agent reads a peer's card; sees `embedding_model` per collection
   (FR-001) and checks it against local config before requesting anything.
2. **Grant** — source operator issues a `knowledge_replica` grant for a specific peer +
   collection (FR-002); independent of any existing `knowledge` (query) grant.
3. **Trigger** — receiver calls the replication trigger; a Replication Job is created and
   returned immediately as a reference (FR-015); the receiver's own `TaskManager` worker runs
   in the background.
4. **Manifest** — worker calls `n2n/knowledge/replicate_manifest`; refuses up front on
   embedding-model mismatch (FR-003) or over-cap size (FR-017) — zero batches requested in
   either refusal case.
5. **Batch pull** — worker calls `n2n/knowledge/replicate_batch` repeatedly (paged), writing
   each page via `ChromaStore.add_chunks()` into the collection (stable name for an initial
   replication, staging name for a re-sync).
6. **Verify & flip** — once the received count matches the manifest, `registry.finalize()`
   flips the `documents` row(s) to `ready` (initial) or the staging→stable swap completes
   (re-sync, D7); only now is the replica queryable (FR-006).
7. **List / audit** — the replica appears in local listings with provenance (FR-008); every
   step above produced an audit record with a GAIT reference (FR-012).
8. **Revoke / delete** — revoking the `knowledge_replica` grant blocks future replication/re-sync
   (FR-011) but does not touch existing local rows; deleting a replica is a separate, explicit
   operator action that removes its `documents` rows and its Chroma collection.
