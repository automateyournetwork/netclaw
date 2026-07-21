# Feature Specification: Knowledge Capability Cards & Knowledge-Aware Routing

**Feature Branch**: `064-knowledge-capability-cards`
**Created**: 2026-07-19
**Status**: Draft
**Input**: User description: "Adjust the A2A Agent Cards to include RAG capabilities (the knowledge base — the actual documents a NetClaw has in its local RAG) as a Skill (so it fits inside the A2A / NCFED capability card), plus instructional adjustments so routing considers remote claws' knowledge bases."

## Overview

Today a claw's A2A capability card ({{NCFED}} §11, built by `inventory.py`) advertises
skills, MCP servers, badges, posture, and LLM tier — but it says nothing about **what a
claw knows**. The RAG knowledge base (feature 062) is invisible to peers, so the only way
a remote claw discovers that another claw can answer questions about a corpus (e.g. John's
book) is to ask it and see. The Hermes↔NetClaw book-summary interop proved the *retrieval*
works over NCFED; this feature makes that knowledge **discoverable and routable** by
advertising each claw's RAG collections as A2A-style entries on the card, and by teaching
the agent to prefer the authoritative peer KB for questions about that peer's domain.

This is a lightweight feature: it extends the existing capability card, adds a small
eN2N knowledge-selection helper and a dedicated `n2n/knowledge/query` method, and updates
the delegation instructions. It adds **no new MCP server** and moves **no document
content** across the federation — only content-free metadata (titles, topics, counts) that
a peer is authorized to see. (The iN2N `router.py` is unchanged; peer selection is an eN2N
concern handled separately.)

## Clarifications

### Session 2026-07-19

- Q: At what granularity should a claw advertise its RAG knowledge on the card? → A: Per collection (one card skill per RAG collection).
- Q: How should a remote claw invoke retrieval against an advertised corpus? → A: A dedicated NCFED method `n2n/knowledge/query` (a method family alongside `n2n/tools/call` / `n2n/tasks/*`, not the MCP proxy), addressable by the advertised `collection_id`, fulfilled by the owner's local RAG composed by its agent. [Refined per analysis H1.]
- Q: How should the querying claw choose which advertised corpus answers a question? → A: Semantic match of the query against each corpus's advertised description; deterministic given the advertised set plus a stable tiebreak.
- Q: Should RAG collections be advertised by default or opt-in? → A: Advertised by default (consistent with skills/MCP servers), with per-peer visibility to hide a collection.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Advertise the knowledge base as an A2A skill on the card (Priority: P1)

A NetClaw operator has documents in local RAG (feature 062). Their claw's capability card
now includes a content-free description of each advertised RAG collection, shaped as an
A2A skill: an id, a human/semantic description of the topics and document titles it covers,
coarse tags (doc types), and document/page counts. A federated peer that pulls the card
(`n2n/inventory_get`) can see *what this claw knows* without seeing the documents
themselves.

**Why this priority**: Discovery is the prerequisite for routing. Without the knowledge
advertised on the card, a peer cannot reason about where to send a knowledge query. This
story alone delivers value: operators and peer claws can enumerate federated knowledge.

**Independent Test**: Ingest a document locally, pull the card as a peer, and confirm the
card lists the collection with its topic description and counts — and contains no chunk
text, no source paths, and no secrets.

**Acceptance Scenarios**:

1. **Given** a claw with a RAG collection containing "Automate Your Network", **When** a
   federated peer fetches its capability card, **Then** the card includes a knowledge skill
   whose description names the corpus topics/titles and reports document and page counts.
2. **Given** the same claw, **When** the card is built, **Then** it contains no chunk
   content, no embeddings, no `source_path`, and passes the existing `_assert_no_secrets`
   check.
3. **Given** a per-peer visibility policy that hides a collection from peer X, **When**
   peer X fetches the card, **Then** that collection does not appear; a permitted peer Y
   still sees it.

---

### User Story 2 - Knowledge-aware routing / delegation (Priority: P1)

When a claw is asked a question whose answer lives in a **federated peer's** advertised
knowledge base rather than its own, it delegates the retrieval to that peer (the
authoritative source) instead of answering from the model alone or declining. The agent's
delegation instructions and an eN2N knowledge-selection helper consult peers' advertised
knowledge entries and select the peer whose collection best matches the query.

**Why this priority**: This is the payoff — it turns advertised knowledge into a working
distributed-RAG answer with correct provenance. It is the generalization of the
Hermes↔NetClaw book demo into deliberate routing.

**Independent Test**: On claw A (no local corpus on topic T) with a federated peer B that
advertises a corpus on T, ask A a T-question; confirm A delegates retrieval to B, returns
B's grounded answer with B's citations, and does not fabricate an answer locally.

**Acceptance Scenarios**:

1. **Given** claw A federated with claw B, where B advertises a knowledge skill matching
   topic T and A has no local corpus on T, **When** A is asked a question about T, **Then**
   A routes the retrieval to B and returns B's cited answer attributed to B.
2. **Given** both A and B advertise collections matching T, **When** A must choose, **Then**
   selection is deterministic (highest embedding-cosine score, then a stable tiebreak by
   peer identity/collection id) and documented.
3. **Given** no federated peer advertises a matching corpus, **When** A is asked about T,
   **Then** A answers from its own knowledge/model and does not invent a federated source.

---

### User Story 3 - Provenance, privacy, and consent on federated knowledge (Priority: P2)

Federated knowledge retrieval is subject to the same default-deny authorization, audit, and
trust-tier rules as any other NCFED invocation. A peer only sees the collections it is
authorized to see; a knowledge query is authorized per peer; every federated retrieval is
audited; and answers carry provenance (which peer, which corpus).

**Why this priority**: The whole value proposition is "knowledge stays home, only answers
travel." That only holds if advertisement and retrieval respect visibility, authorization,
and audit. P2 because P1 stories assume these controls exist (they largely do, via 057/060)
and this story makes them explicit for the knowledge surface.

**Independent Test**: Attempt to fetch a hidden collection and to query a non-granted
corpus from an unauthorized peer; confirm both are refused and audited, and that a
restricted-tier peer sees knowledge advertisement but cannot invoke retrieval.

**Acceptance Scenarios**:

1. **Given** a restricted (self-asserted tier) peer, **When** it fetches the card, **Then**
   it may see authorized knowledge advertisements but any retrieval invocation is denied
   (consistent with {{NCFED}} §6.4 admission tiers).
2. **Given** a possession-tier peer without a grant for corpus C, **When** it requests a
   retrieval against C, **Then** the request is refused (default-deny) and audited.
3. **Given** a successful federated retrieval, **When** the answer is returned, **Then** the
   invocation is recorded in the audit trail with the peer identity, corpus, and a GAIT
   reference.

### Edge Cases

- What happens when a corpus is large or churns often? The advertised description/counts
  must be derived cheaply and refreshed with the card version, not recomputed per query.
- How is a stale card handled? A peer may route to a corpus that has since changed; the
  authoritative retrieval always runs against the owner's live RAG, so the answer reflects
  current content even if the advertised summary lags.
- What if two peers advertise overlapping corpora with conflicting content? Selection is
  deterministic; the answer is attributed to the chosen peer; the design does not attempt
  cross-source reconciliation in this feature.
- What if a peer advertises knowledge but denies the retrieval grant? The querying claw
  treats it as "not available from that peer" and falls back (another peer, or local).
- Empty/again: a claw with no RAG documents advertises no knowledge skill (absence, not an
  empty entry).
- Title sensitivity: because collections are advertised by default (FR-003) and the
  description may include document titles (FR-001), an operator who considers even titles
  sensitive relies on per-peer visibility to hide the whole collection. A topic-only
  description mode (counts/tags without titles) is a reasonable plan-time tunable if
  needed — deferred to planning, not architecture-blocking.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The capability card MUST advertise knowledge at **collection granularity** —
  one A2A-style skill entry per RAG collection — each carrying a stable id, human-readable
  name, a semantic description of the collection's topics/titles, coarse tags, and
  document/page/chunk counts. All content-free.
- **FR-002**: The knowledge advertisement MUST be sourced from the feature-062 RAG document
  registry (title, doc_type, collection, page_count, chunk_count) and MUST NOT include chunk
  text, embeddings, `source_path`, capture commands, or any secret; it MUST pass the
  existing card `_assert_no_secrets` invariant.
- **FR-003**: RAG collections MUST be advertised **by default** (consistent with how skills
  and MCP servers are advertised today). Knowledge advertisements MUST honor per-peer
  visibility: an operator MUST be able to hide a collection from a given peer (reusing the
  existing `n2n_set_visibility` mechanism), and a hidden collection MUST NOT appear in that
  peer's card.
- **FR-004**: Retrieval against a peer's advertised collection MUST be exposed as a
  **dedicated NCFED method** `n2n/knowledge/query` (a member of the method families
  alongside `n2n/tools/call` and `n2n/tasks/*`), NOT the generic MCP `n2n/tools/call`
  proxy — that proxy resolves `server_id/tool_name` against real registered MCP servers and
  cannot address a synthetic knowledge endpoint. The method takes the `collection_id` the
  card advertises (a peer needs no out-of-band knowledge) plus the query, and is fulfilled
  by the owner's local RAG (`rag_search`) composed into an answer by the owner's agent. The
  free-form chat path (proven in the Hermes↔NetClaw interop) MAY remain as a convenience,
  but `n2n/knowledge/query` is the normative, routable interface. The card's `retrieval`
  field names this method.
- **FR-005**: The querying claw MUST select the collection by **embedding cosine
  similarity** between the query and each advertised collection's description, computed with
  the local RAG embedder (feature 062), over both local and federated peers' advertised
  collections. Because the same embedder yields the same vectors, selection is deterministic:
  given the same query and the same advertised set, the same collection is chosen; ties (or
  scores within a small epsilon) break by ascending peer identity then ascending
  `collection_id`. A configurable relevance threshold (env `N2N_KNOWLEDGE_MATCH_THRESHOLD`,
  default `0.5`) gates whether any collection is considered a match.
- **FR-006**: When a **peer** collection scores at or above the threshold and the local claw
  has no local collection scoring higher, the agent MUST delegate retrieval to that
  authoritative peer rather than answer from the model. Fallback order is peer collection →
  local collection → model. When no collection meets the threshold, the claw answers from the
  model and MUST NOT fabricate a federated source.
- **FR-007**: Federated knowledge retrieval MUST be default-deny and authorized per peer,
  admitted only at the possession tier (not self-asserted), and MUST be audited with peer
  identity, collection, and a GAIT reference (consistent with {{NCFED}} §6.4 and feature
  057). The per-peer grant is the human-in-the-loop control point for answering an external
  peer from a local knowledge base (constitution Principle XIV) — no per-call approval is
  required once granted.
- **FR-008**: `n2n/knowledge/query` MUST return an **agent-composed, grounded answer** (not
  raw chunks) carrying provenance — which peer and which collection produced it — and the
  owner's source citations when present, so the requesting agent can attribute the source.
  Composition requires a local agent turn; deployments accept its latency/cost as the price
  of a cited, sovereignty-preserving answer.
- **FR-009**: The delegation/SOUL instructions MUST be updated so a claw, before answering a
  document/factual question, checks whether a federated peer advertises a corpus matching the
  topic and routes accordingly; guidance MUST also cover the fallback order (matching peer →
  local corpus → model) and forbid inventing an authoritative source.
- **FR-010**: The NCFED Internet-Draft capability-card section (§11) MUST be updated to
  document the knowledge skill shape as part of the A2A card mapping, for the next draft
  revision (-01), keeping the on-wire card and the spec in sync.

### Key Entities *(include if feature involves data)*

- **Knowledge entry (card advertisement)**: The A2A-skill-shaped advertisement of one RAG
  collection on the capability card. Attributes: stable `collection_id`, name, semantic
  description (topics/titles), tags (doc types), document/page/chunk counts, and the
  `retrieval` method name (`n2n/knowledge/query`). Content-free. Derived from the RAG
  registry; filtered by per-peer visibility. (Distinct from the **retrieval method**, the
  invocable `n2n/knowledge/query` that returns answers.)
- **RAG collection**: An existing feature-062 grouping of ingested documents in a claw's
  local vector store. The authoritative source; never leaves the owner. ("Collection" is the
  canonical term; earlier drafts also said "corpus".)
- **Knowledge route decision**: The querying agent's selection (via the `knowledge.py`
  selection helper, not the iN2N `router.py`) of which peer collection, local collection, or
  the model should answer a query, with a deterministic embedding-cosine rule and a recorded
  rationale for audit.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A peer fetching a claw's card can enumerate 100% of that claw's authorized RAG
  collections with topic descriptions and counts, and 0% of document content / source paths
  appear in the card.
- **SC-002**: For a knowledge question answerable only by a federated peer's corpus, the
  querying claw delegates to that peer and returns the peer's cited answer in ≥ 95% of trials
  (no local fabrication), matching the Hermes↔NetClaw round-trip already demonstrated.
- **SC-003**: Corpus selection is deterministic — the same query against the same advertised
  set always routes to the same peer/corpus.
- **SC-004**: Every federated retrieval appears in the audit trail with peer identity, corpus,
  and a GAIT reference; unauthorized advertisement fetches and retrievals are refused 100% of
  the time.
- **SC-005**: Advertising knowledge adds no document content to the wire — card size grows
  only by the metadata summary, independent of corpus size.

## Assumptions

- Feature 062 (rag-mcp) is the source of truth for local knowledge; this feature reads its
  registry and reuses its retrieval, and does not change how documents are ingested or stored.
- The NCFED capability card ({{NCFED}} §11, `inventory.py`) and its per-peer visibility,
  admission tiers (§6.4), default-deny authorization, and audit/GAIT trail (features 057/060)
  are reused as-is; this feature adds a knowledge surface on top, not a new trust model.
- The federated retrieval transport already works (proven in the Hermes↔NetClaw book-summary
  interop over the eN2N chat channel); this feature makes the corpus discoverable and the
  routing deliberate rather than introducing a new invocation mechanism.
- "Knowledge" advertised is descriptive metadata only; the owner's live RAG is always the
  thing actually queried, so answers reflect current content even if the advertised summary
  is slightly stale.
- Cross-source reconciliation, ranking answers from multiple peers, and transitive knowledge
  delegation (A asks B who asks C) are out of scope for this lightweight feature.
- **Knowledge replication (RAG2RAG) is explicitly out of scope and reserved for a future
  spec (065).** This feature is *federated query* — knowledge stays home, only the answer
  travels (sovereignty by default). Replicating vectors/chunks across the wire is the
  opposite governance model (the data leaves; revocation becomes best-effort; embeddings are
  effectively document sharing given inversion risk and embedding-model coupling). It has
  real value for availability/offline, volume latency, blended retrieval, and deliberate
  knowledge publishing, but carries a sync/versioning/consent burden this feature avoids.
  064 is a prerequisite for it (discovery before replication). A lighter middle ground —
  answer/chunk caching with TTL and provenance on the querying side — may be worth folding
  in later without a full replication protocol.

## Dependencies

- Feature 062 (rag-mcp) — local knowledge base and retrieval.
- Feature 059 (NCFED Internet-Draft) — capability card (§11) and the A2A mapping the card
  entry must fit; §11 update is a deliverable (FR-010).
- Features 057/060 — admission tiers, per-peer authorization, audit/GAIT, card visibility.
