# Specification Quality Checklist: Federation Inbound-Call Observability

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-08-06
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

### Validation iterations

**Iteration 1 — three failures found and corrected:**

1. **Implementation detail leaked into the spec body.** The originating investigation was expressed in file:line terms (`bgp/agent.py:278`, `service.py:725-753`, `manager.py:289-317`), plus specific identifiers, default values, and function names. All were removed from requirements, scenarios, and success criteria. The Input section retains a prose summary of the operational finding — appropriate as provenance — but names no code locations.
2. **Success criteria were partly untestable.** "Log is readable" and similar were replaced with measurable outcomes: a ≥90% reduction in dead-peer log volume (SC-003), exactly one line and no stack trace for a benign disconnect (SC-004), and identification by visual inspection within seconds under mixed traffic (SC-008).
3. **Requirements stated implementation values as mandates.** Concrete thresholds (summary cadence, staleness horizon, retry ceiling) were reframed as required *properties* — growth permitted, boundedness required, transient failures unpenalised — with the values themselves explicitly recorded as implementation-tunable in Assumptions.

**Iteration 2 — one gap closed:** a fourth noise source was observed live after the first draft (a benign runtime warning on every secure channel closure) and was added as FR-030 / SC-011, with an assumption recording that it originates outside this system's code and therefore calls for reclassification rather than a behavioral fix.

### Deliberate scope decisions

- **The BGP session flap is excluded, and the exclusion is reasoned rather than silent.** It is configuration, not code. But it shares User Story 2's defect shape — a state machine reporting a known-dead peer forever — so Out of Scope requires the feature to answer explicitly whether the dampening principle should extend to BGP session retry reporting, rather than leaving the question open.
- **User Story 1 is P1 over the two noise-reduction stories.** Noise removal only has value because it was concealing the inbound-call signal. A log that is quiet but still silent about inbound calls leaves the operator no better off, so the positive signal is the priority and the dampening stories follow it.
- **User Story 4 is P3.** Automatic dampening (US2) resolves the operational symptom without operator action, so the supported endpoint-retirement operation is a correctness and safety improvement rather than an observability one. It is retained because resolving the live incident required a direct SQL write against the running system's database — precisely what the registry API exists to prevent.

### Cross-cutting constraints worth re-checking at plan time

- FR-003 and FR-019 are explicit anti-suppression guards: authorization denials and unexpected internal faults must survive any dampening mechanism. These are the most likely requirements to be violated accidentally by an aggressive implementation of FR-008 through FR-016, and deserve direct test coverage rather than incidental coverage.
- FR-027 and FR-029 fence the blast radius: audit completeness and wire behavior must be untouched. Any plan that changes protocol or audit semantics to achieve a logging goal has misread the spec.
- FR-012 (transient failures unpenalised) is in direct tension with FR-010 (long-dead peers backed off substantially). The plan must show how a peer is classified into one bucket or the other, and the flapping edge case must be resolved rather than assumed away.
