# Specification Quality Checklist: SNMP-poller NMS coverage (Zabbix)

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-08-03
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs)
  - Zabbix API method names, endpoint shapes and the `pyzabbix` bug are deliberately **absent** from the
    requirements. The behaviours they cause — a default value type that silently returns empty, retention
    windows that silently truncate — are stated as *behaviours*, which is what makes them testable by
    someone who has never read the API docs. Candidate tool counts and licences appear only as evidence for
    the adopt-vs-build decision.
- [x] Focused on user value and business needs
  - Framed on the four questions NetClaw currently cannot answer at all: *is this normal / what did it do
    overnight / how long has it been down / was it like this last Tuesday*.
- [x] Written for non-technical stakeholders
  - The three distinctions are stated in plain terms an operations manager would recognise.
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain
  - Three genuine decisions were surfaced and **all three are now resolved** — see **Decisions taken in
    clarification** below and the `## Clarifications` section of the spec.
- [x] Requirements are testable and unambiguous
  - 58 FRs. The hardest ones (FR-001 through FR-006a) are testable against a real lab by asking for a window
    known to fall outside raw retention, and by choosing an item whose stored type differs from the API
    default. Because they are now **skill obligations** rather than code invariants, they must be tested
    end-to-end through an agent following the skill — asserting on the skill's text would prove nothing.
- [x] Success criteria are measurable
  - 30 SCs. SC-001 is checkable against the NMS's own UI; SC-005 and SC-010 are assertions on **wording**,
    which is the only kind that catches a wording defect.
- [x] Success criteria are technology-agnostic (no implementation details)
- [x] All acceptance scenarios are defined
  - 4 user stories, 18 scenarios.
- [x] Edge cases identified
  - 7, including two that only exist for a monitoring system: **clock skew making a recent window look
    empty**, and **a host that is monitored but has never returned a value** — a real finding that looks
    identical to an absence.
- [x] Scope is clearly bounded
  - Five explicit boundaries (FR-045–FR-049) against Prometheus/Grafana, snmptrap-mcp, ipfix-mcp,
    SaaS monitoring, and the device-reading skills. Out of Scope names eight exclusions.
- [x] Dependencies and assumptions identified
  - Including the one that will bite the schedule: **trends are hourly, so verifying them needs the lab to
    have been polling for hours.**

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation leakage into specification

## Constitutional Alignment

- [x] **Principle I** (safety-first) — **strictly read-only, no write path at all** (FR-021). Read-only is
      forced by NetClaw rather than inherited from an upstream default that is wrong in one of two places
      (FR-021a), with a destructive-method deny-list as a second layer (FR-021b).
- [x] **Principle III** (ITSM-gated changes) — **not applicable: there are no changes.** Recorded as a scope
      decision, not an omission (FR-022). FR-023 requires that any future write arrive with both gates and a
      NetClaw-owned layer, so writes cannot be enabled by flipping a flag.
- [~] **Principle IV** (immutable GAIT audit) — **partially met, knowingly.** No per-call audit: adopting
      as-is means no NetClaw code in the call path, and there is no platform-level MCP audit (measured —
      `~/.openclaw/gait/` holds two files, both NetClaw-authored servers). This is the inherited posture of
      every external integration. Principle IV bites on actions and configuration changes, and this
      integration performs neither (FR-038b). The developer session log is unaffected (FR-038a), and
      FR-038c blocks a future write path from arriving without audit. Recorded, not glossed.
- [x] **Principle VII** (skill modularity) — FR-045–FR-049 keep this from absorbing the trap receiver, the
      flow receiver, the SaaS monitors, or the device-reading skills.
- [x] **Principle X** (observability) — the feature *is* observability, and FR-011/012 make its own answers
      auditable: source, window actually served, and the NMS's own clock.
- [x] **Principle XI** (artifact coherence) — FR-040–FR-044, including both HUD entries and curated profile
      membership.
- [x] **Principle XIII** (credential safety) — FR-028: no credential value in any response, log or audit
      record. FR-029: TLS on by default.
- [x] **Principle XVI** (spec-driven) — this document.
- [x] **Principle XVII** (blog milestone) — waived by standing operator decision.

## Lessons Carried Forward

- [x] **Spec 076** — do not move a shared dependency version. FR-037.
- [x] **Spec 077** — bound submodule-imported pins; use the pip helper, never bare pip. FR-035/036.
- [x] **Spec 078** — record what was *not* exercised rather than claiming it. FR-050/052, SC-025. Also the
      deeper 078 lesson: **an empty result is not a negative finding.** That is literally distinctions 1
      and 2 here.
- [x] **Spec 079** — *no probes ≠ outage* becomes *the poller cannot reach it ≠ the device is down*
      (FR-007, distinction 3).
- [x] **Spec 080** — the two-gate write pattern is **deliberately not built here** because there are no
      writes (FR-022). The other 080 lesson does apply: **passing structural tests do not prove the payload
      is populated**, which is why SC-001 checks values against the NMS's own UI rather than checking that a
      list came back.
- [x] **Spec 081** — typed outcome vocabulary rather than prose. FR-006's four distinguishable absences.
- [ ] **Spec 082** — a guarantee that lives in prose is not a guarantee; put it at a chokepoint the caller
      cannot route around. **This lesson is knowingly NOT applied here.** Adopt-as-is was chosen, so there is
      no chokepoint and FR-001–FR-006 live in the skill. Left unchecked deliberately: it is the one carried
      lesson this feature departs from, and marking it complete would hide that.

## Notes

### What makes this feature's central risk different

Specs 078–082 each guarded a distinction where the wrong answer was at least *visible* — a tool returned
something, and a reader could see what it said. Here, **the two primary failures return HTTP success and an
empty list.** Nothing signals that a mistake was made. An engineer asks "what did this interface do last
month?", gets nothing back, and reasonably concludes the interface was idle or the polling was broken —
when in fact the data exists and NetClaw looked in the wrong place.

That is why FR-001 through FR-006 are stated as obligations on *how the answer is obtained*, not merely on
how it is worded — and why it matters that, following clarification, they are enforced by the skill rather
than by a chokepoint.

### The unusual build-vs-adopt shape

R1, R3 and R9 all rejected community options on quality. R18 rejected one on licence. **This one has a
genuinely good candidate** — three tools, ~823 tokens, 16% of the ceiling, and essentially the design
NetClaw would have arrived at independently.

The catch is structural rather than qualitative: a generic passthrough puts the value-type lookup and the
history/trends routing in the caller's hands, which is exactly where they will eventually be skipped. That
makes this the first feature where *adopt* and *protect the distinction* pulled in opposite directions —
and, following clarification, the first where NetClaw chose adopt and accepted guidance-level enforcement.

### Decisions taken in clarification (session 2026-08-03)

All resolved. Nothing outstanding blocks `/speckit.plan`.

1. **Adopt-vs-build** → **adopt `mpeirone/zabbix-mcp-server` as-is**, GPL-3.0, vendored unmodified with its
   licence intact (FR-034a). The two traps are documented in the skill rather than enforced in code.
   *Consequence, recorded rather than glossed:* FR-001–FR-006 become **skill obligations, not implementation
   guarantees**. This is the first NetClaw integration whose core distinctions are enforced by guidance
   (FR-033a) — a real departure from 080/081/082, bought for smallest-surface and upstream maintenance.
2. **Write path** → **none at all.** R11 is strictly read-only (FR-021). Raised during clarification and
   confirmed: adopt-as-is and gated-writes were **not simultaneously satisfiable**, because the upstream has
   no approval, change-record or audit concept anywhere (verified by inspection — `grep -c` returns 0 across
   all six modules) and enabling writes unlocks every write method at once. Adding writes later requires a
   NetClaw-owned layer, and FR-023 records that so it cannot happen by flipping a flag.
3. **Lab** → **operator-local, not committed** (FR-none; Assumptions + Out of Scope). The quickstart
   documents the build. *Consequence:* the verification is reproducible only by someone who rebuilds the lab.

### Findings from inspecting the adoption candidate

Verified by cloning and reading the source, not from its README:

- **The shipped launcher inverts the safe default.** `utils.py:29` defaults `READ_ONLY` to `True`;
  `scripts/start_server.py:139` defaults it to `False`. Running it the documented upstream way **enables
  writes**. NetClaw must force the flag itself (FR-021a) and add a destructive-method deny-list as a second
  layer (FR-021b), because one of the two upstream defaults is already wrong.
- **No gate machinery exists to hook into** — no approval, change-record, GAIT or audit concept in any
  module. Its entire write control is one binary flag plus regex allow/deny lists.
- **Read/write classification is a method-name prefix heuristic** (`get`, `version`, `check`, `export`), not
  a curated list.
- The launcher bug is to be **reported upstream** (FR-034b) rather than quietly worked around.

### Deferred to planning (not clarification-blocking)

- **Result bounds** — that a bound exists and is stated is fixed (FR-014, SC-017); the specific numbers
  depend on measured payload sizes.
- **Whether an iN2N member gets this** — FR-041 is conditional and already enumerates the obligation.
- **Netdata** — explicitly out of scope here, recorded as a separate near-zero-effort candidate, and the
  roadmap's inaccurate "Cloud MCP" wording to be corrected.
