# Phase 1 Data Model — Open-territory triage (R24)

**Date**: 2026-08-05 | **Plan**: [plan.md](plan.md)

No runtime state. These are the entities the triage document is built from, modelled because the
distinctions between them are what make the output usable.

---

## Entity: Candidate

One named integration target from R24's list.

| Field | Values | Notes |
|---|---|---|
| `name` | free text | e.g. "Arista ANTA" |
| `category` | networking platforms · SP/optical/mobile · SASE/cloud/NaaS · wireless design · adopt-don't-build | R24's own groupings, preserved |
| `disposition` | see below | exactly one, mandatory (FR-001) |
| `reason` | free text | MUST name a blocker, coverer or measurement — never a judgement like "low value" (FR-002) |
| `evidence` | `measured` \| `desk research` | how the assessment was reached (FR-010) |
| `unblocks_when` | free text | **required** when disposition is `DEFERRED` (FR-004) |
| `covered_by` | server or spec id | **required** when disposition is `COVERED` (FR-003) |
| `coverage_confidence` | `verified` \| `claimed` | **required** when disposition is `COVERED` (FR-003) |

---

## Entity: Disposition

Four states. The set is closed — a candidate outside it is a defect, not a fifth case.

| Disposition | Means | Reader's next action |
|---|---|---|
| `COVERED` | the capability is already reachable | do not build; use the named coverer |
| `SELECTED` | worth its own spec, **and verifiable with access on hand** | write the spec |
| `DEFERRED` | worth doing, blocked on a named condition | revisit when the condition holds |
| `DROPPED` | assessed and rejected | do not revisit |

### Why `COVERED` and `DROPPED` are not merged

They lead to different actions. `COVERED` says *the capability exists — go use it*. `DROPPED` says
*this capability is not wanted*. Collapsing them would hide which candidates R1 actually absorbed,
which is the single most useful output of this triage.

### Why `DEFERRED` requires a condition

A deferral without a condition is indistinguishable from an omission, and it is exactly what makes a
list get re-litigated. `unblocks_when` is what turns "not now" into a decision.

### The `coverage_confidence` split

`verified` means someone ran it against the thing. `claimed` means a driver or vendor advertises it
and nobody has demonstrated it here.

This exists because R1 names eight platforms and verified two. Spec 088 (seven registered servers
that could not start) and spec 093 (14 documented tool names that did not exist) are the standing
evidence that this distinction is not pedantry — in both cases the repository asserted a capability
it did not have, and nothing detected it.

---

## Derived: the triage summary

Counts by disposition, plus the `SELECTED` names, are what the roadmap carries (FR-009). Everything
else stays in `TRIAGE.md` so there is exactly one copy (SC-008).

## Validation rules

1. Every candidate has exactly one disposition — no gaps, no doubles (FR-001, SC-001).
2. `SELECTED` count ≤ 2 (FR-005, SC-002).
3. Every `COVERED` has `covered_by` **and** `coverage_confidence` (FR-003, SC-003).
4. Every `DEFERRED` has `unblocks_when` (FR-004, SC-004).
5. No `SELECTED` candidate lacks a documented access check (FR-006, SC-007).
6. Nothing reachable today is `DEFERRED` — it is `COVERED` or `DROPPED` (FR-008).
