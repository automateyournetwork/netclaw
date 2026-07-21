# Contract: Knowledge on the Capability Card + Retrieval Method

Two wire contracts over the existing NCFED channel. Advertisement rides the capability
card; retrieval is a **dedicated NCFED method** `n2n/knowledge/query` (a method family
alongside `n2n/tools/call` and `n2n/tasks/*`) — NOT the generic MCP `n2n/tools/call` proxy,
which resolves `server_id/tool_name` against real registered MCP servers and cannot address
a synthetic knowledge endpoint (analysis finding H1).

## 1. Capability card: `knowledge` array (via `n2n/inventory` / `n2n/inventory_get`)

The card gains a `knowledge` array alongside `skills` / `mcp_servers`. Each element is the
Knowledge Entry (data-model.md). Content-free; visibility-filtered per peer.

```json
{
  "identity": "as65001-4.4.4.4",
  "version": 42,
  "skills": [ ... ],
  "mcp_servers": [ ... ],
  "knowledge": [
    {
      "collection_id": "knowledge:documents",
      "name": "Knowledge: documents",
      "description": "Automate Your Network (John Capobianco) — network automation, Ansible, CI/CD NDLC, data models, templates, reconnaissance, automated documentation.",
      "tags": ["install-guide"],
      "doc_count": 1,
      "page_count": 212,
      "chunk_count": 389,
      "retrieval": "n2n/knowledge/query"
    }
  ],
  "badges": [ ... ],
  "posture": { ... },
  "llm": { ... }
}
```

**Rules**
- A peer that does not understand `knowledge` MUST ignore it (backwards compatible, Const XV).
- `description` MAY omit document titles in topic-only mode (research D5); everything else unchanged.
- The card MUST still pass `_assert_no_secrets`; `collection_id` is opaque and safe to expose.
- Card size grows only with the metadata summary, independent of collection size (SC-005).

## 2. Retrieval: `n2n/knowledge/query` (dedicated NCFED method)

Registered in the service handler map like `n2n/tasks/*`. Invoked with the `collection_id`
the card advertised.

**Request** (`n2n/knowledge/query`):

```json
{
  "collection_id": "knowledge:documents",
  "query": "summarize the book's main topics and takeaways",
  "k": 8,
  "request_id": "as65099-10.255.255.1:7"
}
```

**Result** (agent-composed, grounded answer with provenance — NOT raw chunks; FR-008):

```json
{
  "answer": "Automate Your Network is ... (grounded summary)",
  "provenance": {
    "peer": "as65001-4.4.4.4",
    "collection_id": "knowledge:documents",
    "citations": [
      {"title": "Automate Your Network", "loc": "Preface p.13"},
      {"title": "Automate Your Network", "loc": "Summary p.207"}
    ]
  }
}
```

**Rules**
- Default-deny + possession tier: a self-asserted (keyless) or ungranted peer is refused
  with the standard NCFED authorization error and audited (FR-007; NCFED §6.4, §9.3). The
  per-peer grant is the Principle-XIV human-in-the-loop control point.
- `collection_id` MUST be one the caller is authorized to see; an unknown/hidden id is
  answered exactly as "no such collection" (no existence oracle).
- The callee runs `rag_search` against its **live** RAG and the owner's **agent composes**
  the answer (a local agent turn) with citations when the source provides them.
- One audit record per call: `{peer_identity, collection_id, request_id, decision, gait_ref}`.

## 3. Selection behavior (querying agent + `knowledge.py` helper, not a wire message)

Before answering a knowledge/document question the querying claw MUST:
1. Embed the query with the local RAG embedder and compute cosine similarity against every
   visible advertised collection description (local + peers' cached cards).
2. If a **peer** collection scores highest and ≥ threshold (`N2N_KNOWLEDGE_MATCH_THRESHOLD`,
   default 0.5) → invoke contract #2 against that peer and return its answer with provenance.
3. Else if a **local** collection scores ≥ threshold → answer locally.
4. Else → answer from the model; MUST NOT fabricate a federated source.
Selection is deterministic (same embedder → same vectors → same scores); ties break by
ascending peer identity then `collection_id`. This lives in an eN2N selection helper
(`bgp/federation/knowledge.py`), NOT the iN2N `router.py` (finding H2).
