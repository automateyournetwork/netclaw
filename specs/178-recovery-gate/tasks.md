# Tasks: R07 recovery gate

## Phase 1 — Setup

- [x] T001 Read saved handoff, reserve178 after upstream inspection, create GAIT and three source worktrees; record in specs/178-recovery-gate/verification.md. (FR014,FR018)
- [x] T002 Complete spec, clarification disposition and requirements checklist in specs/178-recovery-gate/. (FR001–FR018)
- [x] T003 Consolidate parallel research, data model and contracts in specs/178-recovery-gate/research.md and contracts/recovery.md. (FR001–FR018)
- [x] T004 Inspect actual retained resources and original retirement receipts; record hashes/status in specs/178-recovery-gate/verification.md. (FR015)

## Phase 2 — Foundations

- [x] T005 Map every prior assertion and uncovered acceptance case in specs/178-recovery-gate/evidence-matrix.md. (FR001,FR017)
- [x] T006 Cross-analyze spec/plan/tasks and record coverage before implementation in specs/178-recovery-gate/analysis.md. (FR001–FR018)
- [x] T007 Freeze isolated runtime/client drill scope, source, evidence and cleanup boundaries in specs/178-recovery-gate/verification.md. (FR014–FR016)

## Phase 3 — US1: same-identity recovery

- [x] T008 [US1] Add real strict-TLS restart/registry endpoint/network-loss regressions in tests/n2n/test_recovery_transport_178.py. (FR002–FR004)
- [x] T009 [US1] Repair demonstrated endpoint/strict dial status gaps in mcp-servers/protocol-mcp/bgp/federation/ and bgp-daemon-v2.py. (FR002–FR004)
- [x] T010 [US1] Qualify actual isolated service restart/address replacement and preserve original IDs/effects in specs/178-recovery-gate/verification.md. (FR002–FR004,FR013)

## Phase 4 — US2: live authority and provider failure

- [x] T011 [US2] Retain failing strict-TLS post-await revocation and expiry regressions in tests/n2n/test_recovery_authority_178.py. (FR005)
- [x] T012 [US2] Fix admission/use/response authority checks and durable revoke-before-close ordering in mcp-servers/protocol-mcp/bgp/federation/internal_channel.py, edge.py, service.py, certs.py and bgp-daemon-v2.py. (FR005)
- [x] T013 [US2] Qualify existing provider outage/unknown-latch behavior with actual prior credit plus affected regressions in tests/n2n/ and specs/178-recovery-gate/evidence-matrix.md. (FR006)
- [x] T014 [US2] Run actual isolated open-channel/reconnect/expiry refusals and retain evidence in specs/178-recovery-gate/verification.md. (FR005,FR013)

## Phase 5 — US3: lost delivery and duplicate/cancel

- [x] T015 [US3] Qualify ordinary task duplicate/cancel/process recovery with actual native MCP in tests/n2n/test_recovery_delivery_178.py; map protected-submit/ACK assertions separately to tests/n2n/test_protected_claims_171.py, test_protected_recovery_171.py and test_protected_combined_176.py plus frozen actual R03 ACK-loss evidence. (FR007,FR008)
- [x] T016 [US3] Repair any demonstrated state transition/replay gap in mcp-servers/protocol-mcp/bgp/federation/ and retain prior actual native ACK-loss credit in specs/178-recovery-gate/evidence-matrix.md. (FR007,FR008)

## Phase 6 — US4: native client recovery

- [x] T017 [P] [US4] Add HUD failing lost-decision/remount, reference recovery and redirect tests in ui/netclaw-visual/test/. (FR009)
- [x] T018 [US4] Persist monotone decision/revoke markers before I/O and implement bounded original-reference recovery in ui/netclaw-visual/src/. (FR009)
- [x] T019 [US4] Add editor same-identity endpoint/ref-preservation regressions and explicit endpoint update in extensions/netclaw-vscode/src/ and test/. (FR010)
- [x] T020 [P] [US4] Add Mobile late-dial/endpoint/identity refusal tests in mobile/netclaw-mobile/test/. (FR011)
- [x] T021 [US4] Implement verified same-host WSS-port update and connection-generation fencing in mobile/netclaw-mobile/lib/. (FR011)
- [x] T022 [US4] Verify actual isolated browser loss/reload/reference recovery and original method/effect counts in specs/178-recovery-gate/verification.md. (FR009,FR013)
- [x] T023 [US4] Verify actual native isolated VS Code loss/endpoint/recovery/wrong-identity refusals with preserved refs in specs/178-recovery-gate/verification.md. (FR010,FR013)
- [x] T024 [US4] Verify actual iOS simulator endpoint/loss/foreground/background/cold recovery and refusals in specs/178-recovery-gate/verification.md. (FR011,FR013)

## Phase 7 — Integration and acceptance

- [x] T025 Integrate reviewed agent commits; run affected broad federation/HUD/editor/Mobile tests/builds and coherence checks in specs/178-recovery-gate/verification.md. (FR001–FR018)
- [x] T026 Write one operator procedure per acceptance row in specs/178-recovery-gate/runbook.md. (FR012,FR017)
- [x] T027 Record observed detection/recovery times and proposed objectives for human agreement in specs/178-recovery-gate/recovery-objectives.md. (FR013)
- [x] T028 Verify private evidence export, owned disposable cleanup and unchanged retained schedules in specs/178-recovery-gate/verification.md. (FR014–FR016)
- [x] T029 Complete evidence/requirements review with no unresolved safety failure in specs/178-recovery-gate/evidence-matrix.md and verification.md. (FR001–FR018)
- [x] T030 Record human timing/roadmap acceptance in specs/178-recovery-gate/verification.md; do not start R08. (FR013,FR018)
- [x] T031 Update memory/2026-11-06.md, relevant infrastructure notes and final GAIT log; prepare specs/178-recovery-gate/resume.md. (FR014,FR015,FR018)

## Dependencies and parallel execution

T001–T003 precede T004–T007; T005/T006 and scoped local T007 are required before
implementation. T004 precedes shared resource work and can run alongside source
preparation. Runtime T008–T016 is serial within its worktree; agent may start with
reproduced US2 bug before independent US1 drills. Surfaces T017–T019 and Mobile
T020–T021 run in parallel after foundations. Native T022–T024 require source tests
and coordinator-approved isolated service ownership; no shared cloud mutation.
T025 follows reviewed lane integration; T026/T027 can grow with observations.
T028/T029 precede final T030/T031. The technical audit/handoff in T031 can close
before the final human response; append its acceptance receipt afterward. All31 tasks must close on actual evidence;
human acceptance is not inferred from implementation progress.

## Implementation strategy

Preserve failing witnesses, implement only demonstrated gaps, verify one story
at a time. Count actual native operations and provider effects. Reuse narrowly
valid historical cloud evidence; new fixtures cannot upgrade its scope.
