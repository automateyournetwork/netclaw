# Specification Quality Checklist: iN2N Production-Mode Enforcement & Durable Runtime

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-07-13
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

- **RESOLVED (2026-07-13)**: FR-019 degraded policy → **per-control**: containment gap (sandbox/model-guard) blocks fail-closed; audit gap (GAIT) allows with `audit-degraded` flag; operator can override to strict-all. Encoded in FR-019/FR-020, SC-008.
- **CLARIFIED (2026-07-13, /speckit.clarify)**: (1) control verification = preflight-gate-per-delegation + background poll for display (FR-003a); (2) always-on member durability = one service per member, single-owner vs cold-start (FR-014/FR-015); (3) GAIT retention = unbounded + git gc, no rotation (FR-012a). Edge cases updated to match.
- All checklist items pass. Ready for `/speckit.plan`.
- **LIVE 6/6 ACHIEVED (2026-07-13)**: `production — enforced` verified end-to-end on the running Border `johns-risk` — a real delegation to the ipfabric member returned live data ("11 snapshots…") while the member ran CONFINED (systemd host-level sandbox) and the DefenseClaw guardrail proxy (:4000) was up; GAIT committed on both Border and member sides; Nick+Byrn stayed federated. Mechanism corrections made during live validation (spec updated): US2 sandbox = **host-level systemd confinement** (OpenShell containers unsuitable for live-infra members — empty, no egress); US3 model-guard = **DefenseClaw guardrail proxy** (`:4000`), and the codebase's `defenseclaw tool inspect` was a non-existent command (fixed → `tool status`); added A2A card posture+LLM advertisement (FR-021) + HUD posture/controls/model + peer posture/model.
- **IMPLEMENTED + LIVE-VALIDATED (2026-07-13)**: all 6 user stories built; 120/120 `tests/n2n/` pass (89 baseline + 31 new 057). Live on the running Border `johns-risk`: posture flips `production — DEGRADED` → `production — enforced` (real OpenShell + DefenseClaw + GAIT); daemon-asserted `security.mode=defenseclaw`; a real production delegation to the ipfabric member returned `enforcement: enforced` and produced an immutable GAIT commit (cross-referenced to SQLite row 56); fault isolation reports daemon/member/backend correctly; Nick (as65007) + Byrn (as65099) stayed `federated` through daemon restarts (SC-007). Real deployment fix found + applied live: the systemd unit needs `~/.local/bin` on PATH or the enforcement CLIs read as "not found" (correctly → degraded, never false-enforced).
