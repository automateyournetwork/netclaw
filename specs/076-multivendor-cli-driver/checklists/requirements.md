# Specification Quality Checklist: Generic Multivendor CLI Driver

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-07-30
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain — the one genuine ambiguity (which library layer owns
      which job, and how this server relates to `pyATS`) was resolved with the maintainer before the
      spec was written and is recorded as a ratified decision
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

### The central ambiguity was resolved before writing, not deferred

"Nornir vs NAPALM vs Netmiko vs pyATS" reads as a four-way tool choice. It is not — they are four
distinct layers (transport / normalization / orchestration / parse-and-test), and Nornir *drives*
Netmiko rather than competing with it. Writing the spec without settling this would have produced
requirements that silently assumed one of two incompatible architectures.

The genuine trade-off is NAPALM (normalized, ~10 platforms) versus Genie (rich, Cisco-deep, ~2000
parsers). Two coherent answers existed:

- **Platform-first** (chosen): dedicated servers own their platforms; this server covers everything
  else, plus cross-vendor normalized reads as an explicit exception.
- **NAPALM-first** (rejected): one uniform shape everywhere, `pyATS` reserved for deep Cisco work.
  Conceptually cleaner but discards most of Genie's parser coverage on NetClaw's most common platform.

Recorded in the spec so it is not re-litigated in planning.

### The exception is the part that needed writing down

NAPALM supports IOS and Junos too, so "use the dedicated server for Cisco" is not a complete rule —
it leaves cross-vendor questions unassigned, and two servers answering the same question in different
shapes is worse than a gap. FR-008 through FR-012 exist to close this precisely: normalized
cross-vendor reads are allowed everywhere, **writes stay single-pathed per platform** (FR-010), and
results say which server answered (FR-011).

The write constraint is a Constitution requirement, not a preference: Principle I requires device
state be verified rather than assumed, and Principle VIII requires post-change verification. Both
become unenforceable if "verified by which tool?" has two answers for one platform.

### Read-only first is deliberately reflected in the priorities

US5 (configuration change) is P3 while three read capabilities are P1/P2. This is not
under-prioritisation — it is the point. Read-only across ~90 platforms is the valuable, safe
increment; writes are the only part that can cause an outage. The spec ships usefulness long before
it ships risk, satisfying the Constitution's "read-only MCP servers are preferred" standard while
still specifying gated writes properly rather than pretending they will never be wanted.

### Evidence gathered before writing

| Claim in spec | How verified |
|---|---|
| 4 platform-bound servers today | `config/openclaw.json` + skill inventory |
| 18 pyATS skills, 1 Junos skill | `ls workspace/skills/` counts |
| `napalm`/`netmiko`/`nornir`/`scrapli` all absent | `importlib.util.find_spec` on each |
| No generic-driver catalog id exists | grep of `scripts/lib/catalog.sh` |
| Lab platforms available for SC-001 | containerlab / GNS3 / EVE-NG already integrated |

The dependency-absence finding matters for planning: this feature pulls a substantial transitive tree
where R0 pulled nothing, so Principle XV (dependency isolation, no conflicts) needs real attention
rather than a nod.

### Scope boundary held

FR-009 and FR-032 exist to stop this feature quietly becoming "rewrite device access." It adds reach
for platforms with none and one cross-vendor read capability. It does not touch `pyATS` or
`junos-mcp`, and their skills must still work unchanged.

## Notes

- Ready for `/speckit.plan`. Phase 0 research owns candidate selection (adopt one, adopt both, or
  fork), the transitive-dependency assessment, and how per-device credentials map onto the existing
  secret store.
- Constitution Principle XVI satisfied: spec ratified before implementation.
- This branch is stacked on unmerged R0. If R0 changes in review, rebase before planning proceeds far.
