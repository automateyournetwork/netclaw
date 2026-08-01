# Specification Quality Checklist: MCP Config Reconciliation

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-07-30
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain — all three resolved by the maintainer on 2026-07-30
      and recorded in the spec's "Resolved Clarifications" section
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable
- [x] Success criteria are technology-agnostic (no implementation details)
- [x] All acceptance scenarios are defined
- [x] Edge cases are identified
- [x] Scope is clearly bounded
- [x] Dependencies and assumptions identified

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak into specification

**Status: PASS — ready for `/speckit.plan`.**

## Validation Notes

### Iteration 1 — the originating premise was wrong

The feature description asserted 20 vendored servers were "silently unregistered." Investigation
found most are deliberately unregistered and already recorded in a 60-entry `EXTERNAL_INTEGRATIONS`
list. Writing requirements against that premise would have produced a feature that registers servers
which are intentionally on-demand. Corrected with a dedicated section, and requirements rewritten
around the real defects.

### Iteration 2 — the real defect was initially missed

Two reconciliation scripts already exist, both report `FAIL` today, and both exit 0, so nothing
enforces them. Now US2 and FR-008, and the feature's centre of gravity rather than a side concern.

Two further failures were measured and folded in: 19 registered servers have no installer catalog
coverage (Principle XI violation) and 9 documented counts are wrong. Silent check degradation also
found — two README claims have drifted in phrasing so `verify-inventory-counts.py` no longer checks
them at all (FR-012, SC-006).

### Iteration 3 — the maintainer's clarification changed the feature's shape

Resolving Question 1 as *"don't worry about the live config as long as all 89 are available for
people when they install their own risk"* moved the goal from config synchronisation to **install
correctness**. Consequences:

- Live-config sync fully descoped; no running agent required (FR-029, SC-013). Removed the former
  live-reachability requirements and the skill-to-running-process tracing, which were premised on
  inspecting a local gateway.
- Installability promoted to US1 and to the first requirements block.
- **This reframing directly surfaced a defect the original framing would have missed**: three
  registered Nautobot servers are hardcoded to `/home/ubuntu/netclaw/`, a path that exists on no
  machine including the one measured — so they are broken for every installer. Now FR-003.
- A fourth registration, `cml-mcp`, packs arguments into its command string; flagged for
  verification rather than asserted broken, since gateway argument handling was not tested (FR-005).
- FR-004 added after noticing the naive form of this check would ban `/usr/bin/python3`. The check
  must distinguish legitimate system paths from machine-specific ones.

### Measurement provenance

Every figure in the spec was produced by running the two existing verifiers or by direct inspection
on 2026-07-30 — 199 skills, 149 integrations, 89 registered, 60 external, 19 uncovered, 9 wrong
claims, 2 unlocatable claims, 9 bypassed directories, 3 foreign-path entries, 1 suspect command.
Nothing is estimated.

### Traceability

| User story | Requirements | Success criteria |
|---|---|---|
| US1 — fresh install obtains all 89 | FR-001 … FR-007 | SC-001, SC-013 |
| US2 — drift caught automatically | FR-008 … FR-013 | SC-002, SC-003, SC-004 |
| US3 — one explained state each | FR-014 … FR-019 | SC-007, SC-009 |
| US4 — documented counts correct | FR-020 | SC-005, SC-006 |
| US5 — one add procedure | FR-023, FR-024 | SC-010 |
| US6 — skill traceability | FR-025, FR-026 | SC-011 |
| Bypassed directories | FR-021, FR-022 | SC-008 |
| Scope discipline | FR-027 … FR-029 | SC-012, SC-013 |

No orphaned requirements; no success criterion lacking a requirement.

## Notes

- All three clarifications resolved. Spec is ready for `/speckit.plan`.
- Constitution Principle XVI (spec-driven development) satisfied: spec ratified before
  implementation.
