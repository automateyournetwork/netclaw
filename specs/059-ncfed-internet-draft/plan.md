# Implementation Plan: NCFED IETF Internet-Draft (`draft-capobianco-ncfed-00`)

**Branch**: `059-ncfed-internet-draft` | **Date**: 2026-07-14 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/059-ncfed-internet-draft/spec.md`

## Summary

Author `draft-capobianco-ncfed-00` (Experimental) — a standards-quality IETF Internet-Draft that **documents the frozen eN2N/iN2N wire protocol** faithfully, compiles clean through `kdrfc`, passes `idnits`, and is ready for Datatracker submission and `agentproto` socialization. **No protocol or code changes** (FR-024). Every normative statement traces to `research.md` (which already resolved all wire facts with file:line citations) and the reference implementation under `mcp-servers/protocol-mcp/bgp/`. Technical approach: write the draft in kramdown-rfc Markdown at `docs/ietf/draft-capobianco-ncfed-00.md`, with RFC ASCII-art for the stack/handshake/frame, a requirement→section fidelity map, and a build/validate/submit pipeline; ship a submission checklist + an agentproto positioning note.

## Technical Context

**Language/Version**: kramdown-rfc Markdown → RFCXML **v3** (via `kdrfc`); Markdown for supporting docs. No application code.
**Primary Dependencies**: `kramdown-rfc` (Ruby gem, provides `kdrfc`), `idnits` (I-D nits checker), `xml2rfc` (invoked by `kdrfc`). Ground-truth source: the reference implementation `bgp/constants.py`, `channel.py`, `agent.py`, `internal_channel.py`, `negotiate.py`, `risk.py` (read-only; cited, not modified). Reference set: RFC 2119/8174/4271/8259 + JSON-RPC 2.0 (normative); RFC 7301/6455/7435/6335/8126, MCP, A2A, `draft-yan-a2a-device-agent-applicability` (informative).
**Storage**: N/A — the deliverable is a document; no runtime state.
**Testing**: `kdrfc` compile (zero errors), `idnits` (zero errors), and a **fidelity cross-check** — every normative wire statement verified against `research.md`/code citations. A completeness review confirms all ~14 core wire facts + all Security Considerations hazards are present.
**Target Platform**: IETF Datatracker (RFCXML v3 upload); renders to TXT/HTML. Authoring on any host with Ruby + the gem.
**Project Type**: Documentation / protocol-specification authoring (single deliverable + supporting artifacts). No src/ or tests/ code.
**Performance Goals**: N/A (document). "Performance" = passes the toolchain and a competent implementer can build an interoperable peer from the text alone.
**Constraints**: **Frozen wire** — the draft MUST NOT contradict or change the implementation; recommendations beyond the code MUST be marked SHOULD/RECOMMEND. Category Experimental with Standards-Track ambition note. IANA: service name `ncfed`, no port. Version: in-band + recommend octet. NCTUN referenced, out of scope.
**Scale/Scope**: One `-00` draft (~15–25 pages typical), ~14 core wire facts, 2 trust models, 2 error registries, 5-part Security Considerations, 3 ASCII diagrams.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Relevance | Status |
|-----------|-----------|--------|
| **XVI. Spec-Driven Development** | specify → clarify (done) → **plan (this)** → tasks → implement. | ✅ On track |
| **XII. Documentation-as-Code** | The deliverable *is* documentation, authored as versioned source (kramdown-rfc) that compiles + validates in CI-style checks (`kdrfc`/`idnits`). Exemplary of the principle. | ✅ |
| **IV. Immutable Audit Trail / honesty** | The draft must be *truthful* to the running protocol (FR-023) — same honesty ethos as the rest of the project; no over-claiming. | ✅ Enforced by the fidelity cross-check |
| **XI. Full-Stack Artifact Coherence** | No new MCP server / skill / installer component — this documents an existing protocol; the code-artifact matrix does **not** apply. The one coherence touch: a README/docs pointer to the published draft. | ✅ (minimal — doc pointer only) |
| **XV. Backwards Compatibility** | FR-024: **zero** wire/code change; the frozen eN2N/iN2N core (052/053/056/057) is untouched. New dev tooling (`kramdown-rfc`, `idnits`) is author-local, not a runtime dependency. | ✅ |
| **XVII. Milestone Documentation** | Submitting an I-D is a milestone → a WordPress blog draft is warranted at completion. | ✅ Noted for post-implement |

**No violations.** Complexity Tracking not required. *(Note: the constitution is written for MCP/skill capabilities; this is a documentation feature, so most code-oriented principles are N/A rather than violated.)*

## Project Structure

### Documentation (this feature)

```text
specs/059-ncfed-internet-draft/
├── spec.md              # (done) requirements + clarifications
├── research.md          # (done) Phase 0 — all wire facts + external landscape, cited
├── plan.md              # This file
├── data-model.md        # Phase 1 — draft section model + wire-fact↔code fidelity map + error registries
├── quickstart.md        # Phase 1 — build/validate/submit pipeline (kdrfc, idnits, Datatracker)
├── contracts/
│   ├── draft-outline.md         # normative section outline + per-section content contract + FR mapping
│   └── ascii-diagrams.md        # the 3 required RFC ASCII-art figures (stack, handshake, frame) — spec + draft art
├── checklists/
│   └── requirements.md  # (done, passing)
└── tasks.md             # /speckit.tasks (NOT created here)
```

### Deliverable (repository)

```text
docs/ietf/
├── draft-capobianco-ncfed-00.md   # THE deliverable: kramdown-rfc source (author here; kdrfc → .xml/.txt/.html)
├── SUBMISSION-CHECKLIST.md         # kdrfc compile, idnits triage, RFCXML v3, Datatracker steps, BCP 78/79
├── AGENTPROTO-POSITIONING.md       # venue (agentproto BoF/WG), ISE fallback, draft-yan differentiation talking points
├── MILESTONE-NOTE.md               # Constitution XVII blog seed (present to John before publishing)
└── captures/
    └── ncfed-johns-risk-nick-20260714.pcap   # live AS65001↔AS65007 capture; cited by the RFC 7942 Implementation Status appendix (committed evidence)
```

The RFC 7942 Implementation Status appendix (informative ref `RFC7942`) documents running code + the capture, honestly scoped to flow-level (ciphertext) evidence.

*(Build outputs `.xml`/`.txt`/`.html` are generated, not committed — added to `.gitignore`.)*

**Structure Decision**: The **draft source lives in `docs/ietf/`** (a real, buildable artifact with a natural home, alongside its submission checklist + positioning note), while the SDD design artifacts (section model, diagram spec, fidelity map, build guide) live under `specs/059-…/`. This separates "the thing we submit to the IETF" from "how we planned/verified it," and keeps the draft discoverable for future revisions (`-01`, etc.).

## Complexity Tracking

> No Constitution violations — table intentionally empty.
