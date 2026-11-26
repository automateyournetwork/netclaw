# Tasks: Spec199 Staged AWS Qualification

Source work and live evidence are distinct. Owner ratified ordered scope and USD100 AWS budget; conservative non-AWS ceilingUSD10. No stage skipping. Checkmarks require the stated evidence, not a plan alone.

Final checkpoint (2026-11-26): **39/39 complete** for the owner-approved Ohio three-AZ scope. All stages accepted/retired; 27 final cells and native/fault evidence verified; 83 tracked final cloud resources and DNS absent. Billing lag and AWS cross-region deferral remain explicit. See [closure](closure-20261126.md).


## Phase 1 — Setup and SDD
- [x] T001 Preserve owner baseline and create/select199 context; record scope/budget in `USER.md`, `memory/2026-11-25.md` and GAIT. (FR-001,009,020; SC-011)
- [x] T002 Write owner-aligned stories/requirements/checklist in `specs/199-aws-multicloud-ha/spec.md` and `checklists/requirements.md`. (FR-001–022)
- [x] T003 Research actual Ohio account/image/quota/price/credit/permission and inherited runtime constraints in `specs/199-aws-multicloud-ha/research.md`. (FR-002; SC-001)
- [x] T004 Write plan/data-model/contracts/quickstart and update agent context for `specs/199-aws-multicloud-ha/`; retain external region gate. (FR-001–022)
- [x] T005 Analyze requirement/task coverage, stage order and constitutional coherence; record findings in `specs/199-aws-multicloud-ha/verification.md` before implementation. (SC-012)

## Phase 2 — Foundational lifecycle controls
- [x] T006 Write negative read-only preflight tests for denial versus empty inventory, quotas, image owner and redaction in `labs/cloud/aws/spec199/test_preflight.py`. (FR-002,020; SC-008,012)
- [x] T007 Implement bounded read-only AWS CLI preflight and private receipts in `labs/cloud/aws/spec199/preflight.py`; verify actual Ohio reads. (FR-002; SC-001)
- [x] T008 Test stage skipping, expired packets, budgets/reserves, duplicate/unknown attempts and concurrent reservations in `labs/cloud/aws/spec199/test_campaign.py`. (FR-001,003–006; SC-001,008,009,012)
- [x] T009 Implement private atomic stage-aware campaign/ledger validation in `labs/cloud/aws/spec199/campaign.py`. (FR-001,003–006,020; SC-001,009)
- [x] T010 Test foreign/default resources, immutable IDs, changed request/token, export failure and repeated absence in `labs/cloud/aws/spec199/test_lifecycle.py`. (FR-006,008,009; SC-008,010,012)
- [x] T011 Implement exact AWS plan/apply/reconcile/export/cleanup graph in `labs/cloud/aws/spec199/lifecycle.py`; no speculative unknown-create retry. (FR-006,008,009; SC-010)
- [x] T012 Verify exact cloud stop-role/schedule permissions, tests and failure behavior in `labs/cloud/aws/spec199/test_watchdog.py` and `watchdog.py`; register account limitations in verification. (FR-005,007; SC-008,009)
- [x] T013 Freeze the full first-stage resource/cost/deadline/safeguard packet and preservation baseline; require a fresh packet for each later stage through `labs/cloud/aws/spec199/campaign.py`; exact cost records live privately. (FR-002–009; SC-001,009,011)

## Phase 3 — US1 single Border
Goal: one actual AWS Border and fresh local member with full native recovery.
Independent test: SC-002. T013 plus all applicable foundational checks block activation.
- [x] T014 [US1] Add AWS host/network inputs around current payload/one-voter preparation in `labs/cloud/aws/spec199/qualify.py`, preserving existing `labs/ha/r09_prepare.py` behavior. (FR-009,010,022)
- [x] T015 [US1] Test payload ownership and one-voter/no-HA labeling in `labs/cloud/aws/spec199/test_qualify.py`; run affected role/protocol regressions. (FR-010,022; SC-012)
- [x] T016 [US1] Activate only the exact single Ohio Border and fresh scoped local member; record real kernel/OpenShell/guard/TLS/DNS evidence in `specs/199-aws-multicloud-ha/verification.md`. (FR-002,007,009,010; SC-001,002)
- [x] T017 [US1] Verify actual local native read and original result/ACK, HUD/Code approval/cold recovery in `specs/199-aws-multicloud-ha/verification.md`. (FR-010,018; SC-002,007)
- [x] T018 [US1] Record Mobile impact/coherence decisions and late stopped-guard evidence in `specs/199-aws-multicloud-ha/verification.md`; export stage1 receipt. (FR-019–022; SC-008,011)

## Phase 4 — US2 physical AWS member
Goal: actual separately identified cloud execution. Independent test: SC-003; US1 receipt required.
- [x] T019 [US2] Parameterize fresh AWS Linux member build/enrollment in `labs/cloud/aws/spec199/qualify.py` using `labs/ha/r09_member.py`; validate lazy imports and short Unix relay before providers. (FR-009,011)
- [x] T020 [US2] Test missing dependencies/relay/foreign identity refusals in `labs/cloud/aws/spec199/test_qualify.py`. (FR-011,022; SC-008,012)
- [x] T021 [US2] Activate exact physical AWS member and verify actual read/placement/signed result/ACK in `specs/199-aws-multicloud-ha/verification.md`; export stage2 receipt. (FR-011; SC-003)

## Phase 5 — US3 brief Ollama and teardown
Goal: bounded CPU tool task and prompt retirement. Independent test: SC-004; US2 receipt required.
- [x] T022 [US3] Add narrowly validated Spec199 ownership to `labs/ollama/qualify.py` with corresponding `tests/n2n/test_ollama_qualification_176.py` regressions. (FR-009,012,022)
- [x] T023 [US3] Implement exact evidence-first Ollama resource removal through `labs/cloud/aws/spec199/qualify.py`, covering preserved-container/network stop semantics. (FR-008,012)
- [x] T024 [US3] Run bounded real guarded CPU task, record original outcome/counts/result/ACK and final late faults in `specs/199-aws-multicloud-ha/verification.md`. (FR-012,019; SC-004,008)
- [x] T025 [US3] Export and verify exact Ollama absence; settle known usage/hold unknowns and stage3 receipt in `specs/199-aws-multicloud-ha/verification.md`. (FR-008,012; SC-004,009,010)

## Phase 6 — US4 three-AZ Ohio AWS
Goal:3AZ-separated Borders/3physicalmembers,9pairs,actual successor. Independent test: SC-005; US3 receipt/cleanup and three observed Ohio AZs required.
- [x] T026 [US4] Obtain observed three-AZ Ohio access, aggregate six-vCPU quota, prices and permission evidence and record fresh scope-bound packet in `specs/199-aws-multicloud-ha/verification.md`; preserve the unresolved other-region SCP denial as a deferred limitation. (FR-002,013; SC-001)
- [x] T027 [US4] Implement explicit Ohio three-AZ scope, same-region pairwise VPC peering orientation, per-host costs and observed AZ-ID binding alongside strict region parameterization in `labs/cloud/aws/spec199/lifecycle.py` and `qualify.py`. (FR-013,014)
  `regional_run.py` freezes/prices the graph, applies once, records region/AZ-bound custody, verifies routes and performs export-gated cleanup/repeated absence. Stage4 recorded39actual custody objects and six verified directed routes; T029/T030 live acceptance and retirement subsequently passed.
- [x] T028 [US4] Test explicit three-AZ scope, actual zone identities, aggregate quotas/costs, same-region route orientation, original strict three-region rejection, stale manifests, route ownership and measured-timing policy in `labs/cloud/aws/spec199/test_regional.py`; run authority regressions. (FR-013,014,022; SC-008,012)
- [x] T029 [US4] Activate3Borders/3members and complete9named pairs plus actual successor operation in `specs/199-aws-multicloud-ha/verification.md`. (FR-013–015; SC-005)
- [x] T030 [US4] Verify native original-result recovery, late authority/guard faults and export stage4 receipt in `specs/199-aws-multicloud-ha/verification.md`. (FR-018,019; SC-007,008)

## Phase 7 — US5 nine-Border mesh LAST
Goal:3AWS+3Azure+3GCP, separate authorities,27named cells,brief run. Independent test: SC-006; US4 receipt required.
- [x] T031 [US5] Freeze final two-hour Azure/GCP/AWS resource and separate cost-domain packet in `specs/199-aws-multicloud-ha/verification.md`; no prior budget reuse. (FR-001–005,016; SC-001,009)
- [x] T032 [US5] Implement explicit AWS AZ/region provenance in the exact ingress/destination/member matrix and receipt verifier in `labs/cloud/aws/spec199/qualify.py`, reusing multi-peer federation contracts. (FR-016,017)
  The qualification wrappers use `matrix.py`; original signed approval/result/ACK, durable member row, native evidence, exact ingress capture and remote peer-client endorsement are required. Fixture coverage is9/27cells, not live acceptance.
- [x] T033 [US5] Test implicit scope changes, duplicate AZs, relaxed Azure/GCP regions, wrong remote-group/member attribution, grant refusal and stale result substitutions in `labs/cloud/aws/spec199/test_matrix.py`; run existing federation198 regressions. (FR-016,017,022; SC-008,012)
  Tests were separated from `test_qualify.py` to keep cryptographic matrix fixtures distinct from host/model qualification. Existing53federation/contract regressions pass.
- [x] T034 [US5] Freshly activate final nine-Border topology and verify all27named cells with all3AWSmembers represented in `specs/199-aws-multicloud-ha/verification.md`. (FR-016,017; SC-006)
- [x] T035 [US5] Verify native recovery and late fail-closed faults; seal original witnesses/state in `specs/199-aws-multicloud-ha/verification.md`. (FR-018–020; SC-007,008)

## Phase 8 — Closure and coherence
- [x] T036 Quiesce/export/hash-verify all current authority/member state and remove only exact owned cloud/DNS/guard resources using `labs/cloud/aws/spec199/lifecycle.py`; prove direct absence. (FR-007–009,020; SC-010,011)
- [x] T037 Reconcile posted bills with full retained unknown/cleanup reservations and close resource ledger in `specs/199-aws-multicloud-ha/verification.md`; never call invoice lag zero cost. (FR-003,004,008; SC-009,010)
- [x] T038 Run applicable repository/catalog/runtime/client coherence checks and record no-new-integration decisions in `specs/199-aws-multicloud-ha/verification.md`. (FR-021,022; SC-012)
- [x] T039 Record actual acceptance/limits, private deferred milestone, daily memory, GAIT and next-session state in `specs/199-aws-multicloud-ha/README.md` and `verification.md`; no release/push/merge without applicable authority. (FR-020,022; SC-011)

## Dependencies and Execution Strategy
T001–005→T006–013→US1(T014–018)→US2(T019–021)→US3(T022–025)→US4(T026–030)→US5(T031–035)→closure(T036–039). Foundational code can be implemented without regional access; activation cannot bypass any prerequisite. At any blocker, quiesce/retain owned state and reservations, do permitted independent work, record the exact condition. MVP is US1; it does not close later stories.

Parallel research is permitted by the planning skill. Within each story, an independent reviewer could inspect completed tests while the operator collects its already-authorized evidence; no live cloud stages or same-file mutations run concurrently. Actual implementation remains sequential unless separately delegated. Examples: US1 inspect role tests versus read-only image evidence; US2 review relay fixtures versus closure hashes; US3 review removal graph versus model provenance; US4 review routes versus region inventories; US5 review matrix schema versus exported signature verification.
