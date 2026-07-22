# Contract: Knowledge Replication (card field + manifest/batch methods)

Three wire surfaces over the existing NCFED channel: one card field addition (extends
064's `knowledge` array), and two new dedicated methods (alongside `n2n/knowledge/query` and
the `n2n/tasks/*` family) — `n2n/knowledge/replicate_manifest` and
`n2n/knowledge/replicate_batch`. Both new methods require a `target_type="knowledge_replica"`
grant, distinct from the `target_type="knowledge"` grant `n2n/knowledge/query` uses, and are
denied at the self-asserted (tier-0) attestation level, same as query.

## 1. Capability card: `embedding_model` on each `knowledge` entry

```json
{
  "knowledge": [
    {
      "collection_id": "knowledge:documents",
      "name": "Knowledge: documents",
      "description": "Automate Your Network (John Capobianco) — ...",
      "tags": ["install-guide"],
      "doc_count": 1,
      "page_count": 212,
      "chunk_count": 389,
      "retrieval": "n2n/knowledge/query",
      "embedding_model": "BAAI/bge-small-en-v1.5"
    }
  ]
}
```

**Rules**
- A peer that does not understand `embedding_model` MUST ignore it (Const XV).
- Still content-free; still passes `_assert_no_secrets`; still absent for a claw with zero
  ready documents.
- `embedding_model` reflects the source's *currently configured* embedder (research D5), not
  a historical per-document record.

## 2. `n2n/knowledge/replicate_manifest` — compatibility + size check, before any transfer

**Request**:

```json
{
  "collection_id": "knowledge:documents",
  "request_id": "as65099-10.255.255.1:11"
}
```

**Result** (success):

```json
{
  "collection_id": "knowledge:documents",
  "embedding_model": "BAAI/bge-small-en-v1.5",
  "chunk_count": 389
}
```

**Result** (not visible / not found — same shape as 064's no-existence-oracle rule):

```json
{ "not_found": true }
```

**Server-side checks (in order)**: tier-0 denial (`TIER0_DENIED` gains
`"knowledge/replicate"`) → visibility (collection must appear in the requester's filtered card,
no existence oracle otherwise) → `authz.authorize(peer, "knowledge_replica", collection_id)`
default-deny. On success, returns the manifest; no chunk content is sent.

**Client-side checks (before requesting any batch)**: the receiver refuses locally, with no
further calls, if `embedding_model` ≠ its own configured embedder (FR-003) or `chunk_count` >
its own configured `N2N_REPLICATION_MAX_CHUNKS` (FR-017). Both refusals are audited as
outbound-denied with a reason naming the mismatch or the limit — zero batch calls follow.

## 3. `n2n/knowledge/replicate_batch` — one page of chunks

**Request**:

```json
{
  "collection_id": "knowledge:documents",
  "offset": 0,
  "limit": 200,
  "request_id": "as65099-10.255.255.1:12"
}
```

**Result**:

```json
{
  "collection_id": "knowledge:documents",
  "offset": 0,
  "returned": 200,
  "ids": ["chunk_0001", "chunk_0002", "..."],
  "embeddings": [[0.0123, -0.0456, "..."], ["..."]],
  "texts": ["...chunk text...", "..."],
  "metadatas": [
    {"document_id": "doc_ab12cd34ef56", "document_title": "Automate Your Network",
     "chunk_ordinal": 1, "page": 12, "section": "Chapter 1"},
    {"...": "..."}
  ]
}
```

**Rules**
- Gated identically to the manifest call (same grant, same tier check) — a batch request for a
  collection with no active `knowledge_replica` grant is refused exactly like the manifest
  call would be, so a caller cannot skip straight to batches.
- `metadatas` values are restricted to the same safe set FR-004 names — never `source_path`,
  `content_hash`, or capture commands.
- `limit` is server-clamped to a page size the channel's per-frame limit comfortably fits
  (`bgp/constants.py` `NCFED_MAX_PAYLOAD` = 64 KB/frame — the same auto-chunking `channel.py`
  already applies to any oversized single message, `_encode()`/`flags bit0 = continuation`);
  callers should not assume a requested `limit` is honored exactly.
- Applying the same `{offset, limit}` twice (a caller retry) returns the same chunks — batches
  are a deterministic slice of the source's stored order. On the receiving side, writes go
  through `ChromaStore.upsert_chunks()` (Chroma `upsert()`, keyed by chunk `id`), not `add()`,
  so replaying a batch is a safe no-op rather than a duplicate-id error (FR-005 idempotency,
  research D11).

## 4. Job lifecycle — no new methods

Triggering, checking status of, and cancelling a replication or re-sync are **not** new wire
methods — they are local operations on the requester's own `TaskManager`
(`bgp/federation/tasks.py`, feature 053), which is a purely local abstraction (its `status()`/
`result()` calls already support `owner=None` for local callers per its own docstring). The
manifest/batch calls above are made *by* the task's background worker to the source peer; the
job itself is never visible to, or reachable by, the source peer or any other peer.
