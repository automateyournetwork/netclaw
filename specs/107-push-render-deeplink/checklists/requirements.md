# Specification Quality Checklist: Notification tap opens the message it names

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-08-13
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

Validation ran over two iterations.

**Iteration 1 — three failures, all "implementation details leaked":**

1. The Context section and every functional requirement named specific
   identifiers from the codebase (`NotificationDeepLink._handleRemote`,
   `findMessageForNotificationData`, `MessageFeedStore.append`, `pushed_at`,
   `FirebaseMessaging.onMessage`, `wireMessageFeed`, `N2N_EDGE_REPLAY_SETTLE_S`).
   The originating bug report was written in those terms, which made it tempting
   to carry them straight through. Rewritten in behavioral terms — "the message's
   send time as recorded by the sender" rather than the field name, "a live
   connection" rather than the transport. The precise call sites belong in
   `plan.md`, not here.
2. Success criteria cited implementation timings (the 3-second settle, the
   measured millisecond timestamps). Restated from the operator's side: readable
   within 2 seconds of the app becoming interactive; usable screen within 10
   seconds when a message never arrives.
3. Named platform services (FCM, APNs) in requirements. Replaced with "the
   existing push transport", with the specific one pinned in Dependencies via
   spec 103 instead.

**Iteration 2 — one failure, "requirements are testable":**

FR-008 originally read "deduplication should be done first", which states a work
order rather than an observable property and cannot be tested. Reframed as a
gating constraint on FR-007 and backed by User Story 3, which is independently
testable. The ordering is now enforced by story priority (Story 3 is P1, Story 2
is P2) rather than asserted in prose.

**One assumption worth escalating at planning time**, recorded in Assumptions
rather than raised as a clarification because a reasonable default exists: keying
deduplication on send time makes two distinct messages sharing a whole-second
timestamp collapse into one. Acceptable for operator-initiated traffic; a real
risk if automated senders are added later. If planning finds that unacceptable,
the sender would need to stamp a unique message id — which *would* make this a
Border change and push it outside this spec's stated scope.

**Not marked as clarifications** (informed defaults taken, per the workflow's
3-marker limit and its guidance to prefer defaults):

- Bounded wait for a named message: "bounded, then fall back to the feed" with a
  10-second outer limit in SC-007. Exact value is a planning detail.
- Read-state behavior on re-delivery: preserved (FR-006), the non-surprising
  default.
- Approval notifications: continue routing to approvals (FR-009), matching the
  behavior spec 068/073 already established rather than inventing new handling.
