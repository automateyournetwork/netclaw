# Implementation Plan: Open-territory triage (R24)

**Branch**: `097-open-territory-triage` | **Date**: 2026-08-05 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/097-open-territory-triage/spec.md`

## Summary

Assess all 22 R24 candidates against what NetClaw already reaches, assign each exactly one
disposition (`COVERED` / `SELECTED` / `DEFERRED` / `DROPPED`) with a reason precise enough that it is
not re-litigated, and select **at most two** for their own future spec.

The deliverable is a decision document, not a server. The load-bearing work is the **first checklist
item R24 has carried since it was written**: re-testing which platforms remain genuinely unreachable
now that R1's multivendor CLI driver reaches ~90 platform families and names eight of R24's
candidates by name.

## Technical Context

**Language/Version**: None. The deliverable is Markdown
**Primary Dependencies**: None new. The assessment reads existing repository state —
`specs/076-multivendor-cli-driver/spec.md` (R1's platform claims and its verified subset),
`config/openclaw.json` (what is registered), `mcp-servers/` (what is vendored), `workspace/skills/`
(what is reachable in practice) — plus desk research for candidates with no repository footprint
**Storage**: None
**Testing**: Assertion-style self-check against the spec's success criteria — 22 dispositions, ≤2
selected, every `COVERED` names its coverer, every `DEFERRED` names its unblocking condition
**Target Platform**: N/A — documentation
**Project Type**: Roadmap triage. **No MCP server, no skill, no registration**
**Performance Goals**: N/A
**Constraints**: No environment is stood up (2026-08-05 clarification). Verifiability is established
by documented access check, so **every assertion must be traceable to repository state or to named
desk research** — an unsupported claim is the failure mode this feature is most exposed to
**Scale/Scope**: 22 candidates across 5 categories

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Principle | Gate | Status |
|---|---|---|
| **VI. Multi-Vendor Neutrality** | Selection must not favour a vendor for its own sake | **PASS** — dispositions turn on reachability and verifiability, and the criteria are fixed before the candidates are assessed |
| **VIII. Verify After Every Change** | Claims must be checkable | **PASS** — FR-003 and FR-010 force the verified/claimed and measured/desk-research distinctions into every entry |
| **XI. Full-Stack Artifact Coherence** | All touchpoints updated | **N/A by scope** — nothing is registered. `reconcile-mcp.py` must still exit 0, unchanged |
| **XII. Documentation-as-Code** | Decisions live where they are read | **PASS** — FR-009 puts the summary in the roadmap and the detail one link away |
| **XVI. Spec-Driven Development** | specify → clarify → plan → task → analyze → implement | **PASS** — first feature to run the full cycle since the gate landed |

### Post-Phase-1 re-check

No new violations. The design adds no code, no dependency and no registration, so the dependency-pin
and startup surfaces are untouched.

## Project Structure

### Documentation (this feature)

```text
specs/097-open-territory-triage/
├── spec.md                    # written first, then clarified
├── checklists/requirements.md # spec quality gate, all items pass
├── plan.md                    # this file
├── research.md                # Phase 0 — what NetClaw already reaches
├── data-model.md              # Phase 1 — Candidate and Disposition
├── TRIAGE.md                  # THE DELIVERABLE — all 22 dispositions
└── tasks.md                   # Phase 2
```

### Source Code (repository root)

No source changes. One documentation file is edited:

```text
docs/COVERAGE-ROADMAP.md    # R24 section -> summary + link; status board row updated
```

**Structure Decision**: `TRIAGE.md` holds the full table; the roadmap carries counts, the selected
candidates and a link. Same shape spec 093 used with `FINDINGS.md`. Duplicating the table into the
roadmap was explicitly rejected in clarification — two copies drift the first time either is edited,
and the roadmap is already ~1,200 lines.

## The risk this plan is built around

**The failure mode is not missing a candidate — it is asserting coverage that does not exist.**

R1's spec names eight platforms it reaches. Only **Nokia SR Linux** and **FRR** were verified live;
the other six are claimed on the strength of the driver's platform table. This project has been
bitten by exactly that gap twice: spec 088 found seven registered servers that could not start while
the gate passed, and spec 093 found 14 documented tool names that did not exist.

So `COVERED` is split at the evidence line, not the claim line:

- **`COVERED (verified)`** — someone ran it against the thing.
- **`COVERED (claimed)`** — the driver advertises the platform; nobody has demonstrated it here.

A `COVERED (claimed)` entry is still a disposition — it means "do not build a dedicated server for
this" — but it carries different weight, and a reader can tell which they are relying on.

## Phase sequence

**Phase 0 (`research.md`)** — establish what NetClaw already reaches, from repository state: R1's
claimed platform list and its verified subset; the registered server inventory; existing lab tooling
(clab / GNS3 / EVE-NG / CML); and which candidates have acquired a mature MCP since the list was
written.

**Phase 1 (`data-model.md`, then `TRIAGE.md`)** — the disposition model, then the 22 assessments.

**Phase 2 (`tasks.md`)** — dependency-ordered tasks, generated by `/speckit.tasks`.

## Complexity Tracking

*No constitutional violations to justify.*

This is the first feature since spec 084 to run `specify → clarify → plan → tasks → analyze →
implement` in order, which is rather the point: the Principle XVI gate landed in 096, and 097 is the
first feature it governs from the start.
