# Specification Quality Checklist: Cloudflare Tunnel as a Hardened eN2N Transport

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-08-14
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain (resolved in Clarifications session 2026-08-14: additional-option transport, default-off per-peer Access, TCP/private-network tunnel mode)
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

- Grounded in a live incident (2026-08-14): two eN2N mesh peers (`as65001-4.4.4.4`, `as65007-7.7.7.7`) found stuck 21–23 days on stale ngrok addresses via `n2n_health`/`n2n_chat` diagnosis, requiring manual `n2n_forget_endpoint` intervention. Root cause traced against spec 063's actual endpoint-persistence code: it only helps a channel that is *still alive* to announce a new address, which structurally cannot help a channel that's already dead with a rotated ngrok address.
- Explicitly scoped as **complementary to, not overlapping with**, specs 059/060/063 — transport substitution + optional edge hardening, zero wire-format or peer-identity-model changes.
- Three genuine operator decisions were deferred to a Clarifications session rather than guessed: (1) additive vs. exclusive transport adoption, (2) Access edge-gate default-on vs. default-off, (3) tunnel mode (HTTP-terminating-at-edge vs. TCP/private-network opaque-relay). All three resolved 2026-08-14, all three consistent with the "additive, never forces peer/operator migration" philosophy already established by 060's own patched/unpatched-peer rollout model.
- The operator's "not sure I would say opt-in but what would that change?" question on (2) was answered inline in the spec's Clarifications section with the concrete consequence (default-on would force uncoordinated re-credentialing of every existing peer simultaneously) rather than just recording the resolved value — this is the kind of reasoning worth keeping visible for a future re-read of this spec.
