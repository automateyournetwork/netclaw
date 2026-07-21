# Phase 0 Research: Knowledge Capability Cards & Knowledge-Aware Routing

All open decisions were resolved in the clarify session (2026-07-19); no `NEEDS
CLARIFICATION` remain. This file records the decisions with rationale and rejected
alternatives.

## D1 — Advertisement granularity

- **Decision**: One knowledge skill per RAG **collection**.
- **Rationale**: Matches RAG's native grouping (the `collection` column in the documents
  registry); keeps the card compact and its size independent of corpus size (SC-005);
  limits title exposure vs. per-document.
- **Alternatives rejected**: Per-document (card bloat, broad title exposure); single
  rolled-up skill (too coarse for useful routing).

## D2 — Retrieval invocation

- **Decision**: A dedicated **invocable knowledge-retrieval skill**, addressable from the
  corpus id the card advertises, invoked via `n2n/tools/call` and fulfilled by the owner's
  local agent/RAG (`rag_search`). Free-form chat retained as a convenience.
- **Rationale**: Deterministic and routable; A2A-clean (a skill with a stable id); no
  out-of-band corpus ids. The chat path (proven Hermes↔NetClaw) stays for humans/ad-hoc.
- **Alternatives rejected**: Chat-only (unstructured, non-deterministic to route); async A2A
  task as the primary path (overhead for a fast lookup — remains available for long jobs).

## D3 — Query → corpus selection

- **Decision**: **Semantic match** of the query against each advertised collection's
  description, over local + federated corpora, made **repeatable** by a stable tiebreak on
  peer identity when scores are close.
- **Rationale**: Mirrors how RAG already works (semantic), robust to paraphrase; determinism
  requirement (FR-005) satisfied at the selection layer by the stable tiebreak, not by
  forcing literal matching.
- **Alternatives rejected**: Tag/keyword only (misses paraphrase); caller-names-corpus only
  (pushes the burden to the requester, though it remains available as an explicit override).

## D4 — Advertise posture

- **Decision**: Collections advertised **by default** (as skills/MCP servers are today),
  hidden per peer via the existing `n2n_set_visibility`.
- **Rationale**: Consistent with existing card behavior and maximizes discoverability, which
  is the point of the feature; sensitive corpora are hidden per peer, and a topic-only
  description mode is available as a plan-time tunable (see D5).
- **Alternatives rejected**: Opt-in per collection (safer but inconsistent with the current
  card model and less discoverable; operator can still achieve opt-in behavior by hiding all
  and un-hiding selectively).

## D5 — Title exposure (deferred tunable)

- **Decision**: Advertise document titles inside the collection description by default; make
  a **topic-only** description mode (counts/tags, no titles) an available configuration.
- **Rationale**: Titles aid routing precision; a minority of operators consider titles
  sensitive and, under advertise-by-default (D4), need a way to suppress them without hiding
  the whole collection. Not architecture-blocking → configuration, decided at implementation.

## D6 — Reuse vs. new surface

- **Decision**: Reuse `inventory.py` (card), `router.py` (selection), `invocation.py`/
  `gateway.py` (retrieval turn via `rag_search`), and the existing visibility / admission
  tier / default-deny / audit-GAIT machinery (057/060). No new MCP server or store.
- **Rationale**: Constitution XI/XV — additive, coherent, backwards compatible.
- **Alternatives rejected**: A standalone "knowledge federation" service (unjustified
  complexity; duplicates card/auth/audit).
