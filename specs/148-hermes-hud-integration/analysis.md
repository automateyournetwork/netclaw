# Specification analysis and remediation record

**Date**: 2026-10-10. **Branch**: `148-hermes-hud-integration`.
**Scope**: Spec, research, plan, data model, contracts, tasks and constitution v1.2.1. Read-only detection followed by a separate remediation pass, explicitly authorized by the owner's instruction to automatically address all findings. This is the pre-implementation analysis record. Implementation results and final design refinements are now recorded in [validation.md](validation.md).

**Result**: Ready for implementation. All 13 actionable design/artifact findings below were corrected and rechecked; no unresolved analysis findings. This is artifact readiness, not live Hermes certification. Platform, policy and acceptance gates remain unchecked implementation work.

## Findings and disposition

| ID | Category / severity | Location | Finding and applied correction | Task coverage | Status |
|---|---|---|---|---|---|
| I1 | Preservation / HIGH | runtime-selection contract; plan architecture | Upstream default database paths would write owner state. Require private response/idempotency factories and session-store injection before construction, plus no-op memory checkout and zero-owner-write tests. | T012,T022,T034 | Resolved |
| I2 | Evidence / HIGH | data model; Hermes contract | Native transcript intervals can change during compaction. Added companion-owned actual invocation/result records bound to immutable request scope; history corroborates rather than defines proof. | T008,T017,T033 | Resolved |
| A1 | Ambiguity / MEDIUM | research R1; runtime capabilities | Model options may contact a provider catalog. Replaced no-provider-request wording with no inference/operational tools, with bounded 60-second cached catalog discovery. | T013,T041–T042 | Resolved |
| U1 | Missing contract / MEDIUM | data model; HUD/MCP contracts | Explicit uncertainty acknowledgment lacked a route/record. Defined authenticated new-conversation request, owned uncertainty reference and durable acknowledgment without unlocking/replaying the old request. | T029–T032 | Resolved |
| C1 | Coherence / HIGH | task setup | New bridge source would be ignored by repository-wide MCP rules. Added explicit source exception and private cache/env exclusions to component setup. | T002,T049,T058 | Resolved |
| I3 | Compatibility / HIGH | runtime-selection contract | Removing repository dotenv fallback could break existing OpenClaw credentials. Added explicit preserving literal import/actionable preflight and seeded conflict tests; Hermes never implicitly imports it. | T034–T035 | Resolved |
| U2 | Selection / HIGH | runtime-selection contract | Home override could retain a stale persisted config path. Defined invalidation unless an explicit config override is supplied, with mixed-home golden tests. | T004–T005 | Resolved |
| I4 | Platform / HIGH | plan; runtime-selection contract | Python-only selection would add a Windows prerequisite. Added portable Node resolver for HUD/Windows and Unix Python bootstrap sharing identical golden contract fixtures. | T004–T005,T038 | Resolved |
| I5 | Compatibility / HIGH | technical context; research R2 | Hermes Node 22 qualification could read as a shared ceiling. Explicitly retained OpenClaw >=24.16,<25 or >=26.1 with separate regression execution. | T036,T038,T051 | Resolved |
| U3 | Launch identity / HIGH | runtime-selection contract | HERMES_HOME does not identify code/interpreter. Added private verified absolute launch/source/interpreter metadata and revision/hash checks; no guessed venv or browser path. | T012,T034,T036 | Resolved |
| I6 | Task format / MEDIUM | tasks story phases | Story tasks needed explicit US labels. Added ordered `[USn]` labels and validated all 58 task lines/IDs. | Artifact correction | Resolved |
| I7 | Task precision / LOW | T056 | Release task named nonexistent root manifests. Restricted it to VERSION/CHANGELOG and real release-linked manifests under CONTRIBUTING conventions. | T056 | Resolved |
| I8 | Stage accuracy / LOW | spec/checklist/generated agent context | Earlier text still said planning had not started; generated context could imply completed code. Updated stage, counts, delegated workflow and planned-only technology notes. | Artifact correction | Resolved |

No constitution violation remains in the design. The private MCP registration exception is explicit and follows the existing private HUD component precedent; all other coherence touchpoints have tasks. The protected Hermes companion is a qualification requirement, not an assumed safeguard. The initial supported tool lane is qualified read-only operations; writes without an independently enforcing policy stay unavailable. Federation execution is reserved for spec 149.

## Functional coverage

The table lists substantive implementation and targeted verification tasks, not merely the final all-requirements regression task.

| Requirement | Has task? | Primary task IDs | Coverage |
|---|---|---|---|
| FR-001 | Yes | T004–T005,T010–T014,T034–T039 | Selection, fresh-shell/custom-home launch, defaults/upgrades. |
| FR-002 | Yes | T009–T013,T018–T019,T038 | Real selected runtime; no OpenClaw/provider bypass. |
| FR-003 | Yes | T013–T014,T036,T041–T045 | Staged readiness and honest capabilities. |
| FR-004 | Yes | T018–T022,T026,T032 | Real contextual Hermes answers; no heuristic fallback. |
| FR-005 | Yes | T003,T015–T018,T022,T024,T033 | Eligible installed tools/skills and actual invocation evidence. |
| FR-006 | Yes | T015–T016,T021–T022,T031,T037 | Enforced boundaries, denied writes/bypass, existing approvals. |
| FR-007 | Yes | T023,T025–T028,T032,T046 | Chat/Canvas/local Avatar and saved work. |
| FR-008 | Yes | T006–T008,T017–T019,T023–T026,T029–T033 | Server/browser ownership, expiry and scoped evidence. |
| FR-009 | Yes | T007,T023–T025 | Owned history list/reopen/continuation. |
| FR-010 | Yes | T013,T041–T045 | Selected metadata/config/log/usage/tool/skill sources. |
| FR-011 | Yes | T020,T041–T042,T045 | Confirmed selections or unavailable controls; actual model. |
| FR-012 | Yes | T034–T035,T039,T041–T044 | Selected-source edits, preservation and redaction. |
| FR-013 | Yes | T023,T028,T045 | Truthful runtime-native navigation. |
| FR-014 | Yes | T010,T013–T014,T018–T019,T029–T032 | Bounded deadlines and actionable failure states. |
| FR-015 | Yes | T006,T008,T018,T029–T033 | Durable unknown outcome and zero automatic replay. |
| FR-016 | Yes | T006–T008,T012,T015–T019,T023–T024,T029,T031,T033,T041–T044 | Credentials, access controls, expiry, isolation, private service. |
| FR-017 | Yes | T007,T011–T012,T025,T034–T039 | Installation/config/credential/skill/browser migration safety. |
| FR-018 | Yes | T009,T021,T027–T028,T034–T046 | OpenClaw regression and accurate Hermes limits. |
| FR-019 | Yes | T001–T003,T022,T036–T040,T047–T058 | Version/platform qualification, coherence, docs, live evidence. |
| FR-020 | Yes | T015–T016,T021–T022,T029,T033,T048 | Terminal Intent uses selected boundary; unsupported APPLY denied. |
| FR-021 | Yes | T006–T007,T023,T025–T026,T028,T034,T039 | Origin-aware persistence and private memory/history. |
| FR-022 | Yes | T008,T018–T020,T026,T029–T032 | Progress, exact approval, truthful stop, preserved drafts. |

## Success criteria and required evidence

| Criterion | Build/test tasks | Acceptance record |
|---|---|---|
| SC-001 | T003,T015–T022,T050 | T053,T055: real five-turn/context/tool on each qualified environment. |
| SC-002 | T023–T028,T033 | T052–T053,T055: views/branches/history/isolation. |
| SC-003 | T004–T005,T010–T012,T034–T044 | T051,T053,T055: zero unselected I/O/writes. |
| SC-004 | T013–T014,T041–T046 | T051–T053,T055: truthful controls/panels. |
| SC-005 | T006,T008,T029–T033 | T051,T053,T055: bounded failures, no replay. |
| SC-006 | T015–T019,T021,T023–T024,T029,T031,T033,T041–T044 | T051–T053,T055: denied writes, expiry, privacy, no secret projection. |
| SC-007 | T034–T040,T050 | T051–T055: preserved data and separate platform/live results. |

## Metrics and final checks

- 6 stories; 22 functional requirements; 7 buildable success criteria: **29/29 covered (100%)**.
- 58 ordered unchecked tasks: US1 5, US2 8, US3 6, US4 6, US5 5, US6 7; setup/foundation/completion 21.
- No unmapped tasks: cross-cutting tasks map to requirements and/or constitution/coherence obligations.
- Detection passes completed: duplication, ambiguity, underspecification, constitution alignment, coverage and inconsistency. No unresolved ambiguity, duplication, critical, high, medium or low findings.
- Structural checks: task IDs/labels/paths, requirement IDs, artifact links, absent template placeholders, whitespace and stage claims checked. Shared-file tasks remain sequential; parallel examples are limited to non-conflicting test/docs work.
- `python3 scripts/verify-spec-artifacts.py`: PASS, 132 specs checked, 4 existing legacy exceptions.
- `git diff --check`: PASS. Spec Kit prerequisites recognize all required design and task artifacts.
- Live Hermes tests, application tests and platform certification have **not** run in this documentation stage. Their implementation tasks remain unchecked; source review does not satisfy them.

## Next action

Report the implementation-ready scope to the owner, then use the implementation phase to execute tasks in order. After Mac implementation/testing, T054 determines whether the offered Windows/WSL machine switch is needed and prepares the exact handoff; T055 keeps required Linux/WSL validation open until completed. No switch is needed for planning. No spec 149 artifacts or federation backend are included.
