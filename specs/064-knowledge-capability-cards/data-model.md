# Phase 1 Data Model: Knowledge Capability Cards & Knowledge-Aware Routing

No new persistent store. This feature derives an on-wire structure from the existing RAG
registry and adds an in-memory routing decision. Entities below are (1) the card knowledge
skill (wire), (2) its source rows (read-only), and (3) the routing decision (in-memory).

## Entity: Knowledge Skill (card entry — wire)

One per advertised RAG collection, embedded in the capability card under a new `knowledge`
array (sibling of `skills`, `mcp_servers`). Content-free.

| Field | Type | Source | Notes |
|-------|------|--------|-------|
| `collection_id` | string | `"knowledge:" + collection` | Stable, addressable id passed to the retrieval method (FR-004). |
| `name` | string | derived | Human label, e.g. "Knowledge: documents". |
| `description` | string | from registry (titles/topics) | Text embedded for cosine selection (FR-005). Titles included unless topic-only mode (D5). |
| `tags` | string[] | distinct `doc_type` values | Coarse classification (e.g. `install-guide`). |
| `doc_count` | int | `COUNT(*)` over the collection | |
| `page_count` | int | `SUM(page_count)` | |
| `chunk_count` | int | `SUM(chunk_count)` | |
| `retrieval` | string | fixed `"n2n/knowledge/query"` | The dedicated NCFED method to invoke with this `collection_id` (FR-004). |

**Invariants**: MUST NOT contain chunk text, embeddings, `source_path`, `content_hash`,
capture commands, or any secret; MUST pass `inventory._assert_no_secrets`. Only collections
visible to the requesting peer appear (FR-003). A claw with zero ready documents emits no
`knowledge` array entries (absence, not empty).

## Entity: RAG Document Registry row (source — read-only)

Existing feature-062 `documents` table. Fields consumed for advertisement: `title`,
`doc_type`, `collection`, `page_count`, `chunk_count`, `ingest_status` (only `ready`
documents are advertised). Never mutated by this feature. `source_path`, `content_hash`,
`capture_commands`, `redaction_counts` are explicitly NOT consumed (secret/PII surface).

## Entity: Knowledge Route Decision (in-memory)

Produced by the eN2N selection helper (`bgp/federation/knowledge.py`, **not** the iN2N
`router.py`) when answering a knowledge query.

| Field | Type | Notes |
|-------|------|-------|
| `query` | string | The knowledge question. |
| `target` | enum | `local` \| `peer` \| `model`. |
| `peer_identity` | string? | Set when `target == peer` (e.g. `as65099-10.255.255.1`). |
| `collection_id` | string? | The advertised `knowledge:<collection>` chosen. |
| `score` | float | Cosine similarity of query vs the chosen collection's description. |
| `rationale` | string | Why chosen (for audit); includes tiebreak/threshold note. |

**Selection rule (FR-005)**: embed the query with the local RAG embedder; compute cosine
similarity against every visible advertised collection description (local + federated
peers); pick the highest scoring at/above `N2N_KNOWLEDGE_MATCH_THRESHOLD` (default 0.5); on a
tie (within a small epsilon) break deterministically by ascending peer identity then
ascending `collection_id`. Deterministic because the same embedder yields the same vectors.
Fallback order when no collection clears the threshold: authoritative **peer** collection →
**local** collection → **model** (FR-006); never fabricate a federated source.

## State / lifecycle

- **Advertisement** refreshes with the card version (`inventory.build` increments `version`);
  it is recomputed from `rag_list`, not per query (performance).
- **Retrieval** always runs against the owner's **live** RAG (`rag_search`), so answers
  reflect current content even if an advertised summary lags (spec Edge Cases).
- **Authorization/audit** reuse the existing per-peer grant + possession-tier gate + GAIT
  audit; a retrieval decision emits one audit record with `peer_identity`, `collection_id`,
  and a GAIT reference (FR-007).
