# Tasks: R04 GCP NetClaw cloud member

Input: spec.md, plan.md, research.md, data-model.md and contracts/. Pass4 of five
bounded implementation passes. No automatic loop. Tests are required by the spec's
security, recovery and actual qualification outcomes.

## Phase 1 — specification and readiness

- [x] T001 Record R04 source choice, existing member/MCP requirement and delegation in specs/173-gcp-cloud-member/spec.md and activation-delegation.md.
- [x] T002 Complete three-lane source assessment and design in specs/173-gcp-cloud-member/research.md, plan.md, data-model.md and contracts/README.md.
- [x] T003 Analyze cross-artifact coverage and resolve HIGH/CRITICAL findings in specs/173-gcp-cloud-member/analysis.md before implementation.

## Phase 2 — shared execution foundation

- [x] T004 Add exact NetBox/subnet variants and immutable MCP/schema/skill bindings in mcp-servers/protocol-mcp/bgp/federation/protected_contract.py, protected_selection.py and adjacent tests.
- [x] T005 Add actual existing MCP execution and reviewed skill context to mcp-servers/protocol-mcp/bgp/federation/protected_runtime.py, protected_docker.py and tests; retain pyATS/OpenClaw/Hermes behavior.
- [x] T006 Add native Linux owned Unix socket broker relay to scripts/protected-inference.py and protected runtime tests; preserve qualified Mac transport.
- [x] T007 [P] Add strict cloud member role validation/launch in scripts/lib/protected_role.py and tests; preserve Border confinement and fail-closed behavior.

## Phase 3 — US1 actual NetBox device reads

Goal: one approved native MCP device read through the actual guarded cloud member.
Independent test: correlate skill/MCP/source/model receipt, signed result and ACK.

- [x] T008 [US1] Add reproducible v2 Bearer/legacy auth and bounded HTTP compatibility for existing NetBox MCP in scripts/lib/ and scripts/lib/install-steps.sh, with actual-source tests.
- [x] T009 [US1] Correct installed singular object types and scoped guidance in workspace/skills/netbox-reconcile/SKILL.md; bind actual reviewed skill source in protected runtime.
- [x] T010 [US1] Verify exact source/schema discovery and choose an observed device through the existing MCP path; record sanitized readiness in specs/173-gcp-cloud-member/verification.md and raw private evidence.
- [x] T011 [P] [US1] Generalize selection identity/wording and verified NetBox result display in ui/netclaw-visual/src/dashboard/RetainedOperationsView.jsx and src/shared/protected-operation-references.js with adjacent tests.
- [x] T012 [US1] Perform actual trusted-HTTPS owner approval and guarded member device read; record native MCP/skill/provider/result/ACK evidence in specs/173-gcp-cloud-member/verification.md.

## Phase 4 — US2 IPAM and subnet

Goal: separately approve prefix read and independently checked bounded calculator.
Independent test: source-prefix agreement and independent arithmetic over actual output.

- [x] T013 [US2] Implement source-pinned prefix/calculator dispatch and bounds in protected_contract.py, protected_runtime.py, protected_docker.py and tests.
- [x] T014 [P] [US2] Add strict verified prefix/subnet summaries and mixed-selection tests in ui/netclaw-visual/src/shared/protected-operation-references.js and dashboard tests.
- [x] T015 [US2] Select observed prefix and bounded calculator arguments through actual MCP readiness; record selection evidence in specs/173-gcp-cloud-member/verification.md.
- [x] T016 [US2] Execute two independent browser approvals and actual guarded MCP calls; independently verify results and signed receipts in specs/173-gcp-cloud-member/verification.md.

## Phase 5 — US3 credential and network isolation

Goal: actual credentials only at member broker/guard; no member-to-member execution.
Independent test: process/IAM/network inspection plus effect-free adversarial probes.

- [x] T017 [US3] Test write/unknown-type/ID/argument/CIDR/destination/redirect/proxy/oversize/error refusals and token non-disclosure in protected runtime and managed NetBox compatibility tests.
- [x] T018 [P] [US3] Add member-only exact-version secret projection and scoped service identities in labs/cloud/gcp/r04/ with tests.
- [x] T019 [US3] Add Docker-aware egress quota, metadata denial and reviewed-link handling in labs/cloud/gcp/r04/host_guard.py with adversarial tests.
- [x] T020 [US3] Build and inspect actual AMD64 agent/guard/relay images and skill/MCP/source closures; retain receipts in private R04 evidence referenced by verification.md.
- [x] T021 [US3] Prove actual secret absence from Border/model/transcript/browser plus process/IAM confinement and public/member peer refusal; record evidence in specs/173-gcp-cloud-member/verification.md.

## Phase 6 — US4 failure and recovery

Goal: unavailable member and same-identity recovery without replay.
Independent test: compare durable attempts/results/ACKs/effect counters before/after.

- [x] T022 [US4] Add mixed-tool uncertainty/restart and status-only HUD recovery tests in protected runtime and ui/netclaw-visual tests.
- [x] T023 [US4] Freeze measured heartbeat/deadline, stop the owned member and observe at least60s of no effect growth plus bounded unavailability, restart and recover same operations; record actual evidence in specs/173-gcp-cloud-member/verification.md.
- [x] T024 [US4] Independently validate native outputs, cryptographic receipts/GAIT and restart counter preservation; retain verifier reports referenced from verification.md.

## Phase 7 — US5 cloud lifecycle

Goal: fresh reproducible finite cloud qualification and zero-residue retirement.
Independent test: exact plans, actual cloud inspection, preserved state and final inventories.

- [x] T025 [P] [US5] Implement fresh isolated two-role IaC/review/host/teardown helpers and budget alert in labs/cloud/gcp/r04/ with source tests; never reuse retired R03 payloads.
- [x] T026 [US5] Refresh cost/access facts, verify budget alert coverage and prepare exact saved IaC/runtime/DNS/bounds/preservation packets; record review in specs/173-gcp-cloud-member/cloud-review.md.
- [x] T027 [US5] Apply fresh saved plans once, provision exact source/secrets and activate/enroll owned roles; record actual receipts in verification.md.
- [x] T028 [US5] Verify actual HTTPS/IAP/services/IAM/firewalls/traffic expiry and capability admission before workloads; record evidence in verification.md.
- [x] T029 [US5] Export current private evidence/state before exact teardown; remove owned resources/DNS/temporary access and verify zero billable residues plus unchanged R01 in verification.md.

## Phase 8 — integration and handoff

- [x] T030 Integrate lane commits; run focused protected/legacy/HUD/build and repository coherence checks, recording outcomes and retained failures in specs/173-gcp-cloud-member/verification.md.
- [x] T031 Complete maintainer artifact-coherence review and qualification matrix in specs/173-gcp-cloud-member/coherence.md; keep release/version/public-rollout hold.
- [x] T032 Update AGENTS.md, USER.md, TOOLS.md, daily memory and GAIT with outcomes/limits; preserve private full gait_log and write specs/173-gcp-cloud-member/resume.md.
- [x] T033 Present independent technical/cleanup evidence for owner acceptance in specs/173-gcp-cloud-member/verification.md; do not begin R04a or R05 before acceptance.

## Dependencies and parallel work

T001–T003 precede all implementation. Broker T004–T006 precede actual MCP and
workload tests. Cloud T007/T018/T019/T025 can run beside broker work. HUD T011/T014
can run beside them once exact result contracts are agreed. T030 source integration
precedes T026–T028 activation. T010/T015 run through staged actual MCP readiness
before final selection; actual cloud T012/T016/T021/T023 require T027–T028.
T024 verifies all live workload/recovery evidence. T029 follows evidence export,
then T031–T033. A task is checked only when its stated source/live outcome exists.

US1 MVP is one approved device read; full R04 requires all five stories. All three
operations retain separate authority/evidence. Implementation tests do not satisfy
live acceptance tasks; unavailable/unknown outcomes are never relabeled complete.
