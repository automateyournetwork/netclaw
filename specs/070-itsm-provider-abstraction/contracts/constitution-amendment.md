# Contract — Constitution Amendment 1.2.0 → 1.3.0 (Provider-Agnostic ITSM Gating)

**Feature**: 070-itsm-provider-abstraction
**Target file**: `.specify/memory/constitution.md` (355 lines at time of writing)
**Version change**: **1.2.0 → 1.3.0 (MINOR)**
**Status**: PROPOSED — **not applied.** This is a reviewable diff for maintainers, produced to satisfy FR-017 and US4. Feature 070 MUST NOT be implemented before this amendment is ratified.

The Constitution names ServiceNow in **five** locations. Amending Principle III alone would leave four references contradicting it, so this amendment is **all-or-nothing across all five** (US4 acceptance scenario 2). Every proposed replacement generalizes existing text to "the configured ITSM" / "a change record" while **preserving each principle's force** — MUST-language intact, lab mode still the sole bypass, bypasses still GAIT-logged. No principle is removed or redefined, which is why this is a MINOR bump under the Constitution's own semantic-versioning rule (`Governance`, lines 344-347: "MAJOR for removals/redefinitions, MINOR for additions, PATCH for clarifications") and per US4 acceptance scenario 3.

Line wrapping in every proposed block follows the file's existing ~72-character convention.

---

### Location 1 — `.specify/memory/constitution.md:55-64` (Principle III: ITSM-Gated Changes)

**Current text (verbatim):**

```
### III. ITSM-Gated Changes

- All production changes MUST have an approved ServiceNow Change
  Request (CR) before execution.
- The CR lifecycle (Assess → Authorize → Implement → Review) MUST
  be followed completely.
- Lab mode is the sole exception — lab devices MAY be modified
  without a CR, but MUST still be GAIT-logged.
- If a CR is rejected or withdrawn mid-execution, the change MUST
  halt immediately and rollback.
```

**Proposed replacement — Variant A (conservative: lifecycle wording kept verbatim):**

```
### III. ITSM-Gated Changes

- All production changes MUST have an approved change record in the
  configured ITSM before execution.
- The configured ITSM is an operator choice (e.g. ServiceNow,
  HaloPSA/HaloITSM, Jira); no specific vendor is mandated.
- The CR lifecycle (Assess → Authorize → Implement → Review) MUST
  be followed completely.
- Lab mode is the sole exception — lab devices MAY be modified
  without a change record, but MUST still be GAIT-logged.
- If a change record is rejected or withdrawn mid-execution, the
  change MUST halt immediately and rollback.
```

**Proposed replacement — Variant B (generalized: lifecycle line also generalized):**

```
### III. ITSM-Gated Changes

- All production changes MUST have an approved change record in the
  configured ITSM before execution.
- The configured ITSM is an operator choice (e.g. ServiceNow,
  HaloPSA/HaloITSM, Jira); no specific vendor is mandated.
- The change record's approval lifecycle MUST be followed completely
  through to its terminal state — in ServiceNow terms, Assess →
  Authorize → Implement → Review.
- Lab mode is the sole exception — lab devices MAY be modified
  without a change record, but MUST still be GAIT-logged.
- If a change record is rejected or withdrawn mid-execution, the
  change MUST halt immediately and rollback.
```

**Rationale:** Generalizes the gating requirement from a ServiceNow CR to an approved change record in the operator's configured ITSM, and adds one bullet making the "no vendor is mandated" reading unambiguous (this is what SC-005 measures) — while keeping MUST-language, lab mode as the *sole* exception, the GAIT-logging obligation, and the halt-and-rollback rule exactly as forceful as before. **Open Question 9 for maintainers:** the "Assess → Authorize → Implement → Review" sequence is ServiceNow's own change-lifecycle vocabulary — HaloPSA and Jira use different state names — so whether to generalize that line is a maintainer decision, not an editorial one. Variant A leaves it untouched (smallest diff, but the line still reads as ServiceNow-specific inside an otherwise vendor-neutral principle); Variant B generalizes it while retaining the ServiceNow sequence as an illustrative example (fully consistent, but a slightly larger change to principle text). **Pick one; do not apply both.**

---

### Location 2 — `.specify/memory/constitution.md:113-114` (Principle VIII: Verify After Every Change)

**Current text (verbatim):**

```
- If rollback fails, the system MUST halt, alert the operator, and
  mark the ServiceNow CR as failed.
```

**Proposed replacement:**

```
- If rollback fails, the system MUST halt, alert the operator, and
  mark the change record in the configured ITSM as failed.
```

**Rationale:** The failed-rollback escalation duty is unchanged in force (halt + alert + mark failed); only the record being marked becomes provider-agnostic, so the obligation is dischargeable in a Halo or Jira shop rather than being literally impossible there.

---

### Location 3 — `.specify/memory/constitution.md:200` (Principle XIV: Human-in-the-Loop for External Communications, inside the approval list)

**Current text (verbatim):**

```
  - Creating, updating, or closing ServiceNow tickets
```

**Proposed replacement:**

```
  - Creating, updating, or closing tickets in the configured ITSM
```

**Rationale:** Keeps the human-approval requirement identical while making it bind for whichever ITSM is configured — otherwise a Halo or Jira deployment could read the list as not covering its own ticket writes, which would *narrow* a safety obligation rather than generalize it. The 2-space list indentation is preserved.

---

### Location 4 — `.specify/memory/constitution.md:260` (Operational Constraints → Technology Stack)

**Current text (verbatim):**

```
- **ITSM**: ServiceNow (change management, incidents, CMDB)
```

**Proposed replacement:**

```
- **ITSM**: operator-selected — ServiceNow, HaloPSA/HaloITSM, or
  Jira/Jira Service Management (change management, incidents, CMDB)
```

**Rationale:** The stack entry becomes a statement of choice rather than a mandate. ServiceNow is deliberately **retained as the first named example**, not deleted — it remains a fully supported provider, and removing it would misrepresent the stack for existing ServiceNow deployments. The parenthetical scope (change management, incidents, CMDB) is unchanged.

---

### Location 5 — `.specify/memory/constitution.md:269` (Forbidden Operations)

**Current text (verbatim):**

```
- Bypassing ServiceNow CR approval for production changes
```

**Proposed replacement:**

```
- Bypassing configured ITSM change approval for production changes
```

**Rationale:** This is the prohibition that gives Principle III teeth; leaving it ServiceNow-specific would make it trivially non-binding for a non-ServiceNow deployment — a *loophole*, not a nuance. The replacement is a single line matching its sibling entries' one-line style, and the neighbouring `- Silent operations without GAIT logging` entry continues to cover the lab-mode bypass.

---

### Footer — `.specify/memory/constitution.md:355`

**Current text (verbatim):**

```
**Version**: 1.2.0 | **Ratified**: 2026-03-26 | **Last Amended**: 2026-07-08
```

**Proposed replacement:**

```
**Version**: 1.3.0 | **Ratified**: 2026-03-26 | **Last Amended**: 2026-07-24
```

**Rationale:** MINOR bump per the Constitution's own versioning rule (generalizing clarification of existing principle text, no removal or redefinition); ratification date is unchanged; `Last Amended` advances to the amendment date.

---

## Proposed Sync Impact Report — replaces `.specify/memory/constitution.md:1-30`

Lines 1-30 are the existing HTML-comment Sync Impact Report block (`<!--` on line 1 through `-->` on line 30). Replace the whole block with the following, which follows the established format and compresses prior versions into "Previous version history" (US4 acceptance scenario 4).

```
<!--
  Sync Impact Report
  ==================
  Version change: 1.2.0 → 1.3.0 (MINOR — provider-agnostic ITSM gating)

  Modified principles:
    - Principle III: ITSM-Gated Changes — "approved ServiceNow Change
      Request (CR)" generalized to an approved change record in the
      configured ITSM, plus an explicit statement that the ITSM is an
      operator choice and no vendor is mandated. Lab mode remains the
      sole exception and is still GAIT-logged; the halt-and-rollback
      rule is unchanged.
    - Principle VIII: Verify After Every Change — the failed-rollback
      escalation now marks the change record in the configured ITSM
      rather than "the ServiceNow CR", so the duty is dischargeable on
      any supported ITSM.
    - Principle XIV: Human-in-the-Loop for External Communications —
      the human-approval list now covers ticket writes in the
      configured ITSM instead of ServiceNow tickets specifically, so
      the obligation does not narrow on non-ServiceNow deployments.
    - Operational Constraints → Technology Stack — the ITSM entry is
      now operator-selected, naming ServiceNow, HaloPSA/HaloITSM, and
      Jira/Jira Service Management; ServiceNow is retained as an
      example, not removed.
    - Forbidden Operations — "Bypassing ServiceNow CR approval" is now
      "Bypassing configured ITSM change approval", closing the loophole
      that made the prohibition non-binding for other ITSMs.

  This is a generalizing clarification of existing principle text — no
  principle is removed or redefined — hence MINOR, not MAJOR.

  Added sections: None

  Removed sections: None

  Templates requiring updates:
    - .specify/templates/plan-template.md — ✅ Compatible (no changes needed)
    - .specify/templates/spec-template.md — ✅ Compatible (no changes needed)
    - .specify/templates/tasks-template.md — ✅ Compatible (no changes needed)

  Follow-up TODOs:
    - Principle III's "Assess → Authorize → Implement → Review" wording
      is ServiceNow's own lifecycle vocabulary; whether to generalize it
      is Open Question 9 of spec 070 and is recorded as a maintainer
      decision (both variants drafted in specs/
      070-itsm-provider-abstraction/contracts/
      constitution-amendment.md, Location 1).
    - Memory MCP's change-reference provenance check remains
      ServiceNow-shaped (^CHG\d+$) and will reject other providers'
      reference formats — deferred, tracked as FR-016 of spec 070.
    - The three nautobot servers (35 gated tools) still use a separate
      gating contract with its own environment scheme; their migration
      onto the shared gate is a specified follow-on phase (FR-014 and
      Open Question 7 of spec 070).

  Previous version history:
    - 1.0.0 (2026-03-26): Initial ratification with 16 core principles
    - 1.1.0 (2026-03-28): Added Principle XVII (Milestone Documentation via
      WordPress)
    - 1.2.0 (2026-07-08): Principle XI installer touchpoint clarification —
      monolithic install script → modular catalog + per-component install
      functions (spec 049)
-->
```

**Note on "Templates requiring updates":** all three are marked `✅ Compatible (no changes needed)` on verified grounds — `.specify/templates/` contains **zero** occurrences of "ServiceNow", "servicenow", "ITSM", or "itsm" (case-insensitive search across the template directory returned no matches). No template asserts anything about the gating ITSM, so none is invalidated by this amendment.

---

## Ratification

**This amendment requires maintainer ratification and MUST NOT be applied unilaterally.**

The Constitution's own `Governance` section (lines 344-347) requires that amendments have (1) a documented rationale, (2) a review of impact on existing principles, and (3) a semantic version bump. This document supplies (1) per location and (3) with its reasoning; (2) is the maintainer review this document exists to enable — including the Variant A / Variant B choice at Location 1 (Open Question 9) and confirmation that all five locations are in scope (Open Question 9's first half).

Sequencing: ratify this amendment first; the code changes of feature 070 land after. Applying any subset of the five locations is worse than applying none, because it leaves the Constitution internally contradictory about whether ServiceNow is mandatory.
