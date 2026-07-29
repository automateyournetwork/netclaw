# Specification Quality Checklist: NCFED Mobile Biometrics and Capture

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-07-22
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

- This is Direction 3 of 3 (final spec) in the NetClaw Mobile initiative.
- A `/speckit.clarify` pass on 2026-07-22 resolved two questions the initial draft left
  ambiguous: (1) captures share the existing NCFED channel and are capped at capture time to
  fit its 16 MB aggregate message bound rather than needing a new transport (verified against
  `bgp/constants.py`'s `NCFED_MAX_MESSAGE`, FR-005a/SC-007), and (2) the operator can disable
  specific Border-requested capture types independently (e.g., audio without photo) rather
  than all-or-nothing, with a disabled type omitted from the inventory entirely rather than
  advertised-but-refused (FR-007a/SC-008).
- The original draft was already explicit on every other scope-defining decision
  (biometric-gates-decision-not-identity, phone as an additional not a replacement approval
  path, both capture directions sharing one mechanism), leaving only implementation-level
  defaults for the Assumptions section beyond the two clarified above.
- FR-003/SC-005 (biometric authentication must never expose the enrollment key) is called
  out as its own testable success criterion, not just a requirement, because it is a real
  security property worth verifying directly rather than assuming from platform vendor
  documentation — this mirrors how other specs in this repo (e.g. 060's certificate work)
  treat security guarantees as things to test, not just design intentions.
- This spec is the first real delivery mechanism behind `notify_approval`, a hook that has
  existed in the code without any wired implementation since before this initiative began —
  worth remembering during planning that there is no existing chat-ops integration to model
  the delivery side after; it is genuinely new.
