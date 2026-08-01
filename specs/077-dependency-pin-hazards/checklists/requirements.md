# Specification Quality Checklist: Dependency-Pin Hazards

**Purpose**: Validate specification completeness before planning
**Created**: 2026-07-31
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain — every figure was measured, not inferred
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable
- [x] Success criteria are technology-agnostic
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

### Every figure was audited, and one was wrong first time

| Claim | How measured |
|---|---|
| `mcp 2.0.0` removed the module | Downloaded the wheel; zero `mcp/server/fastmcp/` files, no `fastmcp` in `Requires-Dist` |
| 7 servers exposed | Cross-referenced unbounded pins against actual `mcp.server.fastmcp` imports |
| 188 pip installs (143 bare `pip3`, 46 bare `pip`, 2 venv-scoped) | Counted in `install-steps.sh` |
| 2 `ensurepip`-dependent venv creations | Grep across `scripts/` |

**A correction is recorded in the spec.** The first audit treated exact `==` pins as unbounded, so it
named the wrong servers — `f5-mcp-server` (`mcp==1.4.1`) and `meraki-magic-mcp-community`
(`fastmcp==2.2.10`) are safe. The total is coincidentally still 7; the membership is not. Recorded
because a spec whose figures shift silently is worse than one that shows its corrections.

### Why this is P1/P1 rather than P1/P2

US2 (enforcement) is equal priority to US1 (repair), not lower. Three hazards survived because nothing
checked for them, and the repair alone would leave the next `mcp 3.0` to be discovered the same way.
This mirrors spec 075, where the enforcement story was co-equal with the cleanup.

### Deliberate scope limits, stated rather than implied

- **Declared pins only.** Transitive breakage needs a lockfile strategy this repository does not have.
- **Pinning `<2` is the default repair**, not migration to standalone `fastmcp`. Migration is legitimate
  where a server wants the new API but is a much larger per-server change, and forcing it would turn a
  hygiene fix into seven rewrites.
- **Not every unbounded pin is a defect.** The spec distinguishes API-significant dependencies — whose
  submodules are imported — from those used via stable top-level APIs. Demanding upper bounds everywhere
  would produce noise and train people to suppress the check.

### Clarifications resolved (3 questions, 2026-07-31)

1. **Bare pip remediation** → one shared `netclaw_pip_install()` helper, all 188 calls routed through it.
   Not 188 individual edits: the hazard is bare pip *on a split-toolchain host*, and one mechanism means
   one place to fix. The two hand-written correct calls from spec 076 were correct only because that
   author had just been burned — not a repeatable safeguard.
2. **How the gate detects danger** → static import scan of each server's own source, so it cannot rot the
   way `EXTERNAL_INTEGRATIONS` did. **Accepted blind spot, recorded as FR-006b**: a submodule scan catches
   6 of 7 and cannot see top-level API drift, so `n2n-mcp` would not be detected. Documented rather than
   closed with a curated list that would make the gate merely *look* complete.
3. **`n2n-mcp`** → migrate forward to `fastmcp>=2,<3` rather than pinning backwards. **This was not my
   recommendation** — I proposed measuring the working version first, since this server backs the
   federation and pattern-matching from the other six is not reasoning. The maintainer chose migration to
   avoid freezing on 0.x-era API, which is a defensible tradeoff of short-term risk against long-term
   drift.

Because that risk lands on the federation, the migration carries three requirements the other six do not:
verified against a *working federation* rather than by import alone (FR-001b), independently revertable
(FR-001c), and not batched with the six pin changes (SC-002b). Import success is not evidence the
federation still functions.

### A figure I had wrong twice

The pip counts were reported as 188 total / 189 bare across different sections — impossible, and caused by
double-counting lines matching both patterns. Recounted precisely: **188 bare invocations (143 `pip3`,
45 `pip`), 1 interpreter-scoped.** Reconciled across the spec and the roadmap. A spec whose own figures
contradict each other is not trustworthy, so this is called out rather than quietly fixed.

## Notes

- Ready for `/speckit.plan`. Phase 0 should settle: pin-versus-migrate per server, how to classify
  API-significant dependencies without hand-maintaining a list, and whether resolution checking can be
  fast enough to run pre-push.
