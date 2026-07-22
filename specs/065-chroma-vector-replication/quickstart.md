# Quickstart: Chroma-to-Chroma Vector Replication over eN2N

Prove the feature end-to-end on the live mesh — replicate a real corpus (e.g. John's book)
from claw A to claw B without B ever calling an embedding model — then the automated checks.

## Manual walkthrough

1. **Have a corpus and a matching embedder.** Claw A (e.g. AS 65001) has a RAG collection
   ingested (feature 062). Claw B is configured with the **same** `RAG_EMBEDDING_MODEL`.
2. **Check compatibility before asking for anything.** From B, pull A's card
   (`netclaw n2n inventory get as65001-4.4.4.4`) and confirm the `knowledge:documents` entry
   now names its `embedding_model` — compare it against B's own configuration.
3. **Grant replication, distinct from query.** On A, issue a `knowledge_replica` grant for B
   on `knowledge:documents` (separate from any existing query-only `knowledge` grant). Confirm
   B still cannot replicate if it holds only the query grant.
4. **Trigger and watch the job, not a blocking call.** From B, trigger replication of
   `knowledge:documents`. The trigger returns immediately with a job reference; poll its status
   and watch chunk/batch progress advance — the terminal does not hang waiting for the whole
   book to transfer.
5. **Confirm it's really not re-embedding.** While the job runs, confirm no embedder process is
   invoked on B for this operation — the batches carry `embeddings` directly, and B writes them
   through `ChromaStore.add_chunks()` unchanged.
6. **Query the replica locally, offline.** Once the job completes, disconnect B from A (or the
   mesh) and query B's replicated collection directly — it answers from local Chroma, no
   federated round-trip.
7. **Confirm provenance and non-propagation.** List B's local knowledge collections: the
   replica shows source peer `A`, source `collection_id`, and a replication timestamp, and is
   visibly distinct from anything B ingested itself. Pull B's own card as a third peer C:
   confirm the replica does **not** appear in B's outbound knowledge advertisement.
8. **Break it on purpose — mismatch.** Reconfigure B with a different `RAG_EMBEDDING_MODEL` and
   trigger replication of a second collection: confirm it is refused immediately, naming both
   models, before any batch is requested.
9. **Break it on purpose — oversized.** Lower B's `N2N_REPLICATION_MAX_CHUNKS` below A's
   collection size and retrigger: confirm refusal before any batch is requested, naming the
   collection size and the configured limit.
10. **Re-sync.** Add a document to A's collection, then trigger a re-sync from B: confirm B's
    replica now includes the new content with no duplicated chunks from the unchanged portion.
11. **Revoke.** Revoke B's `knowledge_replica` grant on A; confirm a further trigger/re-sync
    from B is refused and audited, while B's existing (now-frozen) replica remains queryable
    until B explicitly deletes it.

## Automated checks (pytest)

```bash
cd ~/netclaw
python3 -m pytest tests/n2n/test_replication_manifest_batch.py \
                   tests/n2n/test_replication_identity.py \
                   tests/n2n/test_replication_lifecycle.py \
                   tests/n2n/test_replication_provenance.py -q
```

Expected coverage:
- Manifest/batch calls denied at tier-0 and without a `knowledge_replica` grant; a query-only
  grant does not authorize either call.
- Embedding-model mismatch refuses before any batch call is made (mocked/asserted zero batch
  calls); size-cap-over refuses the same way.
- Two replicas of same-named collections from two different source peers coexist without
  collision; a replica never merges into or overwrites a locally-authored collection of the
  same name.
- A triggered replication/re-sync returns a job reference immediately; status reflects
  queued/in-progress/complete/failed with chunk progress; an interrupted transfer leaves no
  partially-queryable collection.
- Re-sync replaces (not merges) — final chunk count/content matches the current source
  snapshot exactly.
- Revoking a grant blocks future replication/re-sync but leaves an existing local replica
  untouched; deleting a replica removes all its chunks and registry rows.
- A replica never appears in the receiver's own outbound `knowledge` advertisement unless
  explicitly opted into re-sharing.
- Every action above produces an audit record with peer identity, collection id, and a GAIT
  reference.

## Success signals (from spec)

- SC-001: full book-sized replication completes with zero embedder invocations during import.
- SC-002/SC-008: 100% of mismatched or over-cap attempts refused before any data transfer.
- SC-003: 100% of successful replicas carry correct provenance; 0% confusion with local data.
- SC-004: receiver chunk count exactly matches the source manifest on every successful run.
- SC-005: every replication/re-sync/grant/revocation action audited; unauthorized attempts
  refused 100% of the time.
- SC-006: post-re-sync replica matches the current source snapshot exactly.
- SC-007: triggering requests return immediately; job status is observable at any time.
