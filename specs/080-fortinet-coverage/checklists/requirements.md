# Specification Quality Checklist: Fortinet Coverage (FortiOS / FortiManager / FortiAnalyzer)

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-07-31
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain
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

## Notes

**On "no implementation details":** this spec names concrete NetClaw repository artifacts
(`config/openclaw.json`, `scripts/lib/catalog.sh`, `scripts/reconcile-mcp.py`,
`workspace/skills/fortimanager-ops/SKILL.md`) and concrete verification commands. These are retained
deliberately. Constitution Principle XI makes artifact coherence a **non-negotiable acceptance
condition**, not an implementation choice, and spec 075 exists because three integrations shipped
broken when it was treated as one. FR-039 through FR-043 are therefore requirements, not design.
Candidate server repositories are confined to Assumptions, where they are explicitly labelled as a
research decision deferred to planning — the spec commits to no server.

**Resolved during drafting** (informed defaults, all documented in Assumptions):

| Open question | Default taken | Why |
|---|---|---|
| Writes in scope? | Yes, disabled by default, two distinct gates | Spec 076 precedent: gated writes with real CR checking, shipped. Deferring writes would leave FortiManager's highest-value operation permanently out of reach. |
| Which candidate server? | Undecided — deferred to Phase 0 research | A spec that names a repository has made an engineering decision without evidence. Spec 076 evaluated candidates and built instead; that outcome must remain reachable. |

---

## Post-clarification revalidation (2026-07-31)

`/speckit.clarify` asked 5 questions; all 5 were answered and integrated. The checklist was re-run
against the revised spec — **all items still pass**. Material changes:

| # | Question | Answer | Spec impact |
|---|---|---|---|
| 1 | Live verification target | containerlab FortiGate-VM (permanent free eval) + FortiManager-VM on Hyper-V (15-day trial) | **FortiAnalyzer cut**: US4 removed, analyzer FRs removed, all FR/SC renumbered, Out of Scope entry added. ⚠️ **Reversed 2026-08-01** — see below |
| 2 | Tool-manifest budget | Hard ceiling of **5,000 tokens** | FR-026 became testable; SC-013 now asserts a number instead of an adjective |
| 3 | Plane attribution | **Structural** — `plane` field in every response | New FR-005a: a community server cannot satisfy this unmodified, narrowing build-vs-adopt; new SC-002a asserts it mechanically |
| 4 | Skill topology | **Two skills** — `fortimanager-ops` back-filled + new `fortigate-ops` | FR-002a added; skill count target fixed at 205; both `SKILL.md` files added to the coherence list |
| 5 | Stale iN2N member | **Repair by regeneration** | FR-003 split into FR-003/a/b; scoped as local hygiene, explicitly not installability |

**Two premises I got wrong and corrected mid-session**, recorded so they are not reintroduced:

1. **The FortiGate-VM 15-day trial no longer exists.** Since FortiOS 7.2.1 it is a *permanent* free
   evaluation licence. My first recommendation was built on stale information, and the correction
   changed the lab design from time-boxed to permanent for the device plane.
2. **`migration-staging/` is untracked, and all 27 members share the same generated absolute home
   path.** I had described the fortimanager member as carrying a spec-075 portability defect. It does
   not — the path is the generator's convention, no installer sees it, and only the dangling command
   reference is real. FR-003b now says so explicitly so a later reader does not "fix" 27 generated
   files.

---

## Scope restored (2026-08-01)

**A third premise was wrong, and it was mine.** The Q1 answer cut FortiAnalyzer on the belief that no
analyzer was obtainable. I never verified that — I extrapolated it from the FortiManager trial. It is
false: **FortiAnalyzer-VM ships a free, full-featured 15-day trial, built in, no activation required**,
supporting 6 GB/day of logs. All three planes come from one free FortiCare account.

Reaching a scope decision through an unverified assumption is precisely the failure FR-035/FR-036 exist
to prevent, and it happened inside the clarification process meant to prevent it. The user's question
— "is there any way to get virtual or online sandbox Fortinet stuff?" — is what surfaced it.

**Restored**: User Story 4 (P3), FR-018a/b/c, SC-007a, and the analyzer plane throughout. The
Out-of-Scope entry is deleted. Requirement IDs use letter suffixes rather than a second renumbering of
23 requirements — the convention the spec already uses (`FR-002a`, `FR-005a`, `FR-020a`).

**Follow-on effects**: skill count target moves 205 → **206** (`fortianalyzer-ops` follows from the Q4
one-skill-per-plane rule); `plane` gains a third value; FR-034 changes from "state the analyzer is not
covered" to a cross-plane routing requirement.

**Also ruled out definitively** — FNDN is not a signup: every account requires **sponsorship by two
Fortinet employees**. No hosted Fortinet sandbox with API access exists at any tier.

**New hard constraint on task ordering**: FortiGate's licence is permanent, FortiManager's and
FortiAnalyzer's are **15 days from first boot**. The lab must be staged — FortiGate first for
development, FMG/FAZ booted only at verification time. Booting all three up front would spend the
verification window on implementation.

**Revalidation**: checklist re-run against the restored spec — all items still pass. FR sequence
contiguous (FR-001…FR-041 with documented letter suffixes), SC sequence contiguous, four user stories,
no `[NEEDS CLARIFICATION]` markers, no stale two-plane references.
