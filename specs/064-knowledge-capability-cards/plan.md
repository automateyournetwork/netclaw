# Implementation Plan: Knowledge Capability Cards & Knowledge-Aware Routing

**Branch**: `064-knowledge-capability-cards` | **Date**: 2026-07-19 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/064-knowledge-capability-cards/spec.md`

## Summary

Advertise each claw's local RAG collections (feature 062) as content-free, A2A-style
knowledge skills on the NCFED capability card, and route knowledge queries to the peer whose
corpus is authoritative — generalizing the demonstrated Hermes↔NetClaw book-summary interop
into deliberate, discoverable routing. The card gains one entry per RAG collection (from the
`rag_list` registry: title/topics/doc_type/counts, no content); retrieval is a dedicated
dedicated `n2n/knowledge/query` method addressable from the card and fulfilled by the owner's
agent composing over local RAG (`rag_search`); a new `knowledge.py` helper selects the
collection by embedding-cosine similarity (query vs advertised description) with a configurable
threshold and stable tiebreak. Reuses existing per-peer visibility, admission tiers,
default-deny authorization, and audit/GAIT (057/060). No new MCP server; iN2N `router.py`
untouched.

## Technical Context

**Language/Version**: Python 3.10+ (daemon + `bgp/federation/*`, matching 052–063); Markdown (SOUL/skill docs + NCFED draft §11 for -01)
**Primary Dependencies**: Existing only — new `bgp/federation/knowledge.py` (advertisement builder + eN2N cosine selection), `inventory.py` (card), `invocation.py`/`gateway.py` (retrieval method + agent composition), the feature-062 rag-mcp (`rag_list`, `rag_search`, and its embedder for query vectors). No new third-party packages.
**Storage**: Reuses `~/.openclaw/rag/rag.db` (documents registry, read-only for advertisement) and the issued capability card. Per-peer visibility reuses existing federation.db rows. No new store.
**Testing**: pytest under `tests/n2n/` (card contents, no-secrets invariant, visibility filtering, deterministic selection, tier/authorization/audit on retrieval).
**Target Platform**: Linux (systemd --user mesh/member services), consistent with the live deployment.
**Project Type**: Extension of the existing NCFED daemon + capability card + RAG integration (single-project, in-repo).
**Performance Goals**: Advertisement derived from `rag_list` cheaply and refreshed with the card version (not per query); card growth bounded by metadata only, independent of corpus size (SC-005).
**Constraints**: Content-free card (no chunks/embeddings/source paths; passes `_assert_no_secrets`); retrieval possession-tier only + default-deny + audited; answers carry provenance.
**Scale/Scope**: Small mesh of mutually-known operators (NCFED applicability); tens of collections per claw at most.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Assessment |
|-----------|------------|
| IV. Immutable Audit Trail | PASS — every federated retrieval audited with peer/corpus/GAIT (FR-007), reusing the existing trail. |
| V. MCP-Native Integration | PASS — advertisement reads rag-mcp `rag_list`; retrieval uses `rag_search` via the agent turn; no bespoke data path. |
| VI. Multi-Vendor / Agent Neutrality | PASS — knowledge advertised as an A2A-standard skill on the wire card; any implementation (Hermes, etc.) can consume it without shared code. |
| VII. Skill Modularity | PASS — knowledge exposed as a discrete, self-describing skill entry; no coupling to the requester's internals. |
| IX. Security by Default | PASS — content-free card, per-peer visibility, possession-tier + default-deny retrieval; sovereignty preserved (knowledge stays home). |
| XV. Backwards Compatibility | PASS — additive card field; a peer that ignores `knowledge` is unaffected; chat retrieval path retained. |
| XVI. Spec-Driven Development | PASS — this plan follows the spec; FR-010 keeps the NCFED draft §11 in sync. |
| XI. Full-Stack Artifact Coherence | PASS — plan lists every touchpoint (card, router, SOUL/skill docs, NCFED draft, tests); no orphan surface. |

No violations. Complexity Tracking not required.

## Project Structure

### Documentation (this feature)

```text
specs/064-knowledge-capability-cards/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (card knowledge-skill + retrieval skill)
└── tasks.md             # Phase 2 (/speckit.tasks — not created here)
```

### Source Code (repository root)

```text
mcp-servers/protocol-mcp/bgp/federation/
├── knowledge.py         # NEW: build content-free collection entries from the RAG registry;
│                        #      eN2N cosine selection (query vs advertised descriptions) + threshold
├── inventory.py         # + call knowledge.build_entries() into the card; _assert_no_secrets covers them
├── invocation.py        # + n2n/knowledge/query handler (default-deny, possession-tier, audited, agent-composed answer)
├── gateway.py           # retrieval answer composition reuses the agent turn + rag_search (wiring only)
└── router.py            # UNCHANGED — iN2N RiskRouter is not the eN2N knowledge selector (finding H2)

workspace/skills/n2n-federation/SKILL.md   # + delegation guidance: prefer authoritative peer collection; fallback peer→local→model; never fabricate a source
docs/ietf/draft-capobianco-ncfed-00.md     # §11 note staged for -01 (FR-010) — NOT the live -00 submission

tests/n2n/
├── test_knowledge_cards.py        # advertisement contents, no-secrets, visibility filtering, collection granularity, card-size independence (SC-005)
└── test_knowledge_routing.py      # deterministic cosine selection, threshold fallback, tier/authorization/audit/no-oracle on n2n/knowledge/query
```

**Structure Decision**: Single-project, in-repo extension. A new `bgp/federation/knowledge.py`
holds the advertisement builder and the eN2N cosine selection helper; `inventory.py` and
`invocation.py` wire it into the card and a dedicated `n2n/knowledge/query` method; `router.py`
(the iN2N RiskRouter) is deliberately untouched. No new package, MCP server, or store.

## Complexity Tracking

No constitution violations — section intentionally empty.
