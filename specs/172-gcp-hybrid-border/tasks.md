# Tasks: R03 GCP hybrid Border

Evidence-based completion only. Cloud/DNS/runtime/teardown mutations remain gated
by exact review and delegation. User story acceptance includes actual observations;
unit fixtures do not satisfy live tasks. No release/version/public rollout.

## Phase1 — Specification and foundation

- [x] T001 Preserve accepted R02 and R01 baselines; create Spec172 branch and GAIT session in specs/172-gcp-hybrid-border/resume.md.
- [x] T002 Complete spec, research, plan and contracts in specs/172-gcp-hybrid-border/.
- [x] T003 Independently analyze requirement/task/constitution coverage and freeze contracts in specs/172-gcp-hybrid-border/analysis.md.
- [ ] T004 Create separate implementation worktrees, verify ignores and record pass3 scope in specs/172-gcp-hybrid-border/resume.md.

## Phase2 — US1 four independent device reads

Independent test: four actual approvals, sole-command transcripts, parsed versions,
signed results and durable ACKs; fixtures first establish selection isolation.

- [ ] T005 [P] [US1] Implement immutable profile selector and factory dispatch in mcp-servers/protocol-mcp/bgp/federation/protected_selection.py and protected_runtime.py.
- [ ] T006 [US1] Validate catalog identity uniqueness and exact selector coverage in protected_contract.py and protected_service.py.
- [ ] T007 [US1] Test concurrent profile isolation, substitutions, malformed/edited config and preserved single-runtime behavior in tests/n2n/test_protected_selection_172.py.
- [ ] T008 [P] [US1] Add bounded retained operation references, ID-only recovery and independent result presentation in ui/netclaw-visual/src/dashboard/ApprovedOperationsView.jsx and shared helpers.
- [ ] T009 [US1] Test four-device selection/recovery/unknown states and verified parsed projection in ui/netclaw-visual/src/dashboard/protected-operations.test.js and src/hud-server/protected-server.test.js.
- [ ] T010 [US1] Qualify exact CML host-key provenance and fresh one-device profiles without changing original inventories; record private hashes in specs/172-gcp-hybrid-border/runtime-review.md.
- [ ] T011 [US1] Execute four actual named-HTTPS browser-approved OpenClaw reads and correlate native/provider/receipt/ACK evidence in specs/172-gcp-hybrid-border/verification.md.
- [ ] T012 [US1] Verify scope refusals, disconnect/lost reply/owned restart and unchanged spent counters in specs/172-gcp-hybrid-border/verification.md.

## Phase3 — US2 authenticated control-only deployment

Independent test: production source fixtures then actual HTTPS, host/IAM/process
and external network observations; no provider/device authority on Border.

- [ ] T013 [P] [US2] Implement dedicated protected production entrypoint and exact asset closure in ui/netclaw-visual/protected-server.mjs and src/hud-server/.
- [ ] T014 [US2] Test authority/Origin/proxy/CSRF/cookie/revocation/route/asset refusal and production browser CSP in ui/netclaw-visual/src/dashboard/protected-operations.test.js and src/hud-server/protected-server.test.js.
- [ ] T015 [P] [US2] Implement strict provider-neutral role validator/launcher in scripts/lib/protected_role.py and scripts/protected-role.py.
- [ ] T016 [US2] Enforce role-specific protected configuration and catalog hooks in mcp-servers/protocol-mcp/bgp/federation/protected_service.py.
- [ ] T017 [US2] Add verified control-only posture and dormant private eN2N policy in existing federation production/listener paths with tests.
- [ ] T018 [US2] Render confined non-root federation/HUD/Caddy system units and startup secret projection in labs/cloud/gcp/r03/.
- [ ] T019 [US2] Test role/env/path/source tampering, no ambient-home fallback and service rendering in tests/n2n/test_protected_role_172.py.
- [ ] T020 [US2] Freeze exact runtime/key/secret/source/DNS/TLS activation and scoped repair packet in specs/172-gcp-hybrid-border/runtime-review.md; obtain delegation before execution.
- [ ] T021 [US2] Activate only reviewed services/hostname/private secrets; capture actual systemd/process/identity/IAM evidence in specs/172-gcp-hybrid-border/verification.md.
- [ ] T022 [US2] Verify real DNS/trusted TLS/owner browser/login refusal/CSRF/Origin/revocation and legacy/WS denial in specs/172-gcp-hybrid-border/verification.md.
- [ ] T023 [US2] Verify outbound unchanged-key enrollment, no cloud-to-LAN route, public port policy and zero Border provider/device credentials in specs/172-gcp-hybrid-border/verification.md.

## Phase4 — US3 reproducible bounded infrastructure

Independent test: exact fresh plan/apply, no-drift, finite resource/traffic bounds,
exported evidence and reviewed teardown with no billable residues.

- [ ] T024 [P] [US3] Implement isolated labelled/expiring GCP IaC and provider-neutral host inputs in labs/cloud/gcp/r03/.
- [ ] T025 [US3] Validate IaC formatting/schema and resource isolation using existing OpenTofu; record in specs/172-gcp-hybrid-border/cloud-review.md.
- [ ] T026 [US3] Reconcile accrued billing, total ceiling, finite egress/expiry and residual charges in specs/172-gcp-hybrid-border/cloud-review.md.
- [ ] T027 [US3] Freeze exact saved resource plan/hash, IAM/firewalls/DNS scope and teardown preparation; obtain delegation in specs/172-gcp-hybrid-border/cloud-review.md.
- [ ] T028 [US3] Apply only the delegated new R03 resources and verify no drift/R01 changes in specs/172-gcp-hybrid-border/verification.md.
- [ ] T029 [US3] Verify actual expiry/rate/egress safeguards and collect estimate-versus-observed cost visibility in specs/172-gcp-hybrid-border/verification.md.
- [ ] T030 [US3] Export/verify private audit/results then review exact R03-only DNS/resource teardown in specs/172-gcp-hybrid-border/teardown-review.md.
- [ ] T031 [US3] Execute delegated teardown and verify absent R03 billable residues plus unchanged R01 state in specs/172-gcp-hybrid-border/verification.md.

## Phase5 — Integration and closure

- [ ] T032 Integrate independently tested source lanes; run appropriate protected/legacy/HUD/build regressions and record limits in specs/172-gcp-hybrid-border/verification.md.
- [ ] T033 Independently review security boundaries and actual receipt correlations; remediate findings within remaining bounded passes in specs/172-gcp-hybrid-border/verification.md.
- [ ] T034 Reconcile all FR/SC/task evidence, preserved failures/unknowns and supported platform matrix in specs/172-gcp-hybrid-border/verification.md.
- [ ] T035 Record maintainer-only handoff, current blockers/acceptance and next R04 gate in specs/172-gcp-hybrid-border/resume.md; keep release hold.
- [ ] T036 Record daily memory/GAIT log and obtain human R03 acceptance before R04 in specs/172-gcp-hybrid-border/resume.md.

## Dependencies and parallel execution

T001–T004 precede implementation. Protocol T005–T007, HUD T008–T009/T013–T014,
coordinator T015–T019 and cloud T024–T026 can proceed in separate worktrees after
contract freeze; overlapping protected_service.py is coordinator-owned.
T032 integrates these before cloud/runtime packet freeze. T027→T028 and
T020→T021 require exact delegation; T021–T023 and T010 precede T011/T012.
T029–T031 follow live evidence, export and exact teardown approval. T033 reviews
both source before activation and final actual receipts. T034–T036 close only
when all actual evidence is complete. No missing cloud gate is marked complete
because source tests pass. R04 remains blocked on human R03 acceptance.

## Implementation strategy

Pass3 implements the minimal end-to-end contract with focused tests. Pass4/5 are
reserved for concrete verification findings across R03–R05; use no unbounded
Ralph automation. Source fixes do not authorize extra device/model executions.
