# Tasks: direct cloud transport and TLS identities

**Roadmap**: R01 | **Input**: spec.md, plan.md, research.md, data-model.md, contracts/transport.md
Tests are required by the brief. All filesystem paths below are repository-relative.
No task authorizes cloud spend, account mutations, live device/model calls or publication.

Reconciliation evidence: [verification.md](verification.md#resume-reconciliation--2026-11-01).
T028 is supported by actual Mac/GCP admission, refusal, relocation and explicit-recovery evidence. Full HUD/model/RAG acceptance is recorded separately.

## Phase 1: Setup

- [x] T001 Record baseline and isolated test commands in specs/168-ngrok-transport-contract/verification.md; create private test environment, preserve existing runtimes.
- [x] T002 Add strict dependency pins to mcp-servers/protocol-mcp/requirements.txt and fail-closed installer handling in scripts/lib/install-steps.sh; retain independent certificate helper environment.

## Phase 2: Foundation

- [x] T003 Write actual socket exporter/verification/backpressure/fragmentation/EOF/timeout/cancellation tests in tests/n2n/test_exporter_tls_168.py and observe failures before implementation.
- [x] T004 Implement bounded public-API MemoryBIO asyncio adapter in mcp-servers/protocol-mcp/bgp/federation/exporter_tls.py with chain/SAN verification, TLS1.3 and RFC9266 exporter; pass T003.

## Phase 3: US1 — register and inspect (P1)

Goal: private two-service configuration and owned lifecycle. Independent test:
two isolated installations, invalid schemas/ownership denied, service-specific
status and process stop cannot affect the other installation.

- [x] T005 [P] [US1] Write schema/ownership/bundle/duplicate-address/CAS tests in tests/n2n/test_endpoint_registry_168.py; observe missing implementation failure.
- [x] T006 [P] [US1] Write named-endpoint rendering/two-installation lifecycle tests in tests/n2n/test_ngrok_lifecycle_168.py using fake local executables only.
- [x] T007 [US1] Implement validated owned registry, public bundle import/export and status projection in mcp-servers/protocol-mcp/bgp/federation/endpoint_registry.py.
- [x] T008 [US1] Implement selected private environment, exact named reserved TCP config/unit rendering, PID/start-time/config ownership and bounded audit in scripts/ngrok-control.py; no reservation allocation or global stop.
- [x] T009 [US1] Extend scripts/netclaw and scripts/peering-setup.sh for registry and owned ngrok lifecycle; remove unsafe global process selection from affected path and retain explicit legacy migration instructions.
- [x] T010 [US1] Expose configured/TCP/TLS/admission separately in mcp-servers/protocol-mcp/bgp-daemon-v2.py, bgp/federation/posture.py and ui/netclaw-visual/src/main.js; no secret/path dumps or inferred success.
- [x] T011 [US1] Add private enrollment bundle selection to scripts/lib/setup_enrollment.py and selected-runtime durable configuration in scripts/in2n-services.py; preserve existing local enrollment behavior.

## Phase 4: US2 — authenticated channels (P1)

Goal: both launchers attach to the expected Border through transparent forwarding.
Independent test: real local TLS plus application enrollment/reconnect; separate
NCFED TLS/consent succeeds only for approved identities. Live ngrok is separate.

- [x] T012 [US2] Write positive strict iN2N enrollment/reconnect and eN2N preamble/TLS/consent tests in tests/n2n/test_ngrok_transport_168.py, using different routing and TLS names.
- [x] T013 [US2] Add strict binding and versioned pre-enrollment Border attestation/admission deadline in mcp-servers/protocol-mcp/bgp/federation/internal_security.py, internal_channel.py and service.py; require provisioned application trust before sending token.
- [x] T014 [US2] Wire registry-based TLS listener and both member reconnect paths in mcp-servers/protocol-mcp/bgp-daemon-v2.py and scripts/in2n-member.py; reload current approved registration and never fall back or replay tasks.
- [x] T015 [US2] Add NCFED-only public listener plus explicit TLS name/CA/pre-approved peer trust in mcp-servers/protocol-mcp/bgp/federation/service.py and tls.py; preserve private routing and existing consent/framing.
- [x] T016 [US2] Replace first-tunnel discovery and forbid registry overwrites from peer announcements in mcp-servers/protocol-mcp/bgp-daemon-v2.py and bgp/federation/service.py.

## Phase 5: US3 — negative security and exposure (P1)

Goal: fail closed under adversarial identity/protocol/lifecycle input. Independent
test: every brief refusal class, no routing mutation, member listener or downgrade.

- [x] T017 [US3] Add wrong name/CA/pin/Border identity, altered exporter, forged possession, cross-connection replay and repeated-auth tests in tests/n2n/test_ngrok_transport_168.py.
- [x] T018 [US3] Add expired/replayed enrollment, revoked new/open channel, cleartext/PROXY/TLS1.2 and raw BGP/NCTUN refusal tests in tests/n2n/test_ngrok_transport_168.py.
- [x] T019 [US3] Enforce one authentication exchange and current revocation on open channels in mcp-servers/protocol-mcp/bgp/federation/internal_channel.py and service.py; record bounded denial audit without submitted secrets.
- [x] T020 [US3] Prove member-to-member refusal, outbound-only behavior, both launcher paths, unavailable/reconnect status and no application replay in tests/n2n/test_ngrok_transport_168.py.

## Phase 6: US4 — transport relocation (P2)

Goal: reviewed address changes preserve identity and support explicit recovery.
Independent test: live local channels relocate with unchanged member keys; stale
revision/foreign install fails, outage does not choose older address/profile.

- [x] T021 [US4] Add failed/concurrent updates, explicit recovery and relocation tests in tests/n2n/test_endpoint_registry_168.py and test_ngrok_transport_168.py.
- [x] T022 [US4] Complete address-only update/recovery CLI and sanitized receipts in scripts/ngrok-control.py and mcp-servers/protocol-mcp/bgp/federation/endpoint_registry.py.
- [x] T023 [US4] Document coordinated profile migration, move/clone, state fencing and operator-owned examples in specs/168-ngrok-transport-contract/deferred-docs/NGROK-TRANSPORT.md; qualify transport-only scope and distinguish later runtime migration.

## Phase 7: Coherence, qualification and handoff

- [x] T024 Update README.md, SOUL.md, TOOLS.md, .env.example and existing workspace/skills/n2n-federation/SKILL.md (resolve actual existing skill path before editing); document strict profile and evidence limits without owner account defaults.
- [x] T025 Review existing scripts/lib/catalog.sh, config/openclaw.json and protocol MCP documentation; update descriptions as applicable, regenerate affected catalog/effects artifacts and run scripts/verify-catalog-coverage.py; record unchanged tool/component counts.
- [x] T026 Run focused new and existing direct/internal TLS/eN2N/cloudflared/Hermes/installer/HUD regressions, record commands/UTC/excerpts in specs/168-ngrok-transport-contract/verification.md; fix failures and preserve platform limits.
- [x] T027 Prepare exact live account/endpoint/agent commands in specs/168-ngrok-transport-contract/live-runbook.md; record actual access/limits or UNQUALIFIED, projected R14 inventory and cost uncertainty. Never execute unapproved mutations.
- [x] T028 Perform separately authorized direct-cloud/separate-network positive, negative and recovery qualification and record specs/168-ngrok-transport-contract/verification.md; leave this task unchecked if access/authorization is absent.
- [x] T029 Complete six acceptance groups, G1–G11 and platform/transport portfolio matrix plus XI coherence checklist in specs/168-ngrok-transport-contract/verification.md, allowing explicit UNQUALIFIED/FIXTURE-ONLY status without claiming gate success.
- [x] T030 Draft milestone article and PR body locally in specs/168-ngrok-transport-contract/milestone-draft.md and pr-draft.md; no publication.
- [x] T031 Record session outcome in memory/2026-11-01.md and GAIT; report spec/branch/PR status/evidence/open risks and stop for next. R03 requires human acceptance of actual R01 verification.

## Owner-approved direct-cloud pivot — 2026-11-01

The original tasks above retain their historical evidence. T028 now requires the
owner-selected direct cloud path; ngrok live acceptance is optional and remains
unqualified. No existing pass is relabeled. Finish these additional tasks before
closing the amended R01; no later brief is started.

- [x] T032 Reconcile spec/plan/data model/contracts and roadmap G2/G9 with the approved direct-cloud pivot; preserve original work and audit the supersession.
- [x] T033 Add red/green schema-2 direct registry, bundle, transport-specific validation, CAS/recovery and legacy-ngrok preservation tests; implement in endpoint_registry.py.
- [x] T034 Add explicit direct peering lifecycle/status dispatch using the existing owned daemon controller; refuse ngrok rendering/start for direct registrations and test without starting public services.
- [x] T035 Exercise direct real socket enrollment/NCFED, identity/downgrade/exposure refusals, reconnect/revocation and address relocation; keep ngrok regression evidence separate.
- [x] T036 Prepare exact direct-cloud pilot IaC/configuration/cost/budget/expiry/teardown and approval packet; preserve cloud/spend boundaries and selected-runtime ownership.
- [x] T037 Update docs/HUD/catalog/installer touchpoints and drafts; run relevant regressions/coherence and record fresh results without claiming live qualification.
- [x] T038 Reconcile amended acceptance matrix, tasks, resume, daily memory and GAIT; stop after R01. T028 is backed by actual approved cloud evidence.

- [x] T039 Reconcile deployment-choice guidance through README, setup.sh, installer/catalog, VS Code wizard, operator guides and roadmap; validate touched surfaces. Covers FR025.

- [x] T040 Provision the reviewed cloud HUD and verify its owner-selected full open HTTPS lab workspace, Sonnet-backed member answer and matching on-prem member/cloud Border iN2N enrollment and reconnect evidence; record actual browser/status receipts. Covers FR026; limited subnet demonstration, no device/production acceptance implied.

T036 foundation and exact runtime packets are prepared in cloud-review.md and
runtime-review.md using actual foundation outputs and fresh private material.
Foundation, DNS/HTTPS activation and actual IP relocation are verified. The owner
subsequently delegated the full HUD and Sonnet/subnet demonstration; T040 requires
its actual browser, task/tool correlation and RAG receipts; all are now recorded.

T032 → T033 → T034 → T035 → T036 → T037 → T028 → T038.
FR021/FR023 map to T033; FR010/FR022 to T034–T036/T028; FR024 to T036/T028;
FR001–FR020/SC001–SC008 retain original mappings plus T033–T038 for the pivot.

## Dependencies and implementation strategy

T001→T002→T003→T004→US1→US2→US3→US4→coherence. T005/T006 can be written
in parallel (different files). US2 integration follows registry ownership; US3
attacks completed transport; US4 reuses admission. Shared service.py edits are
sequential. Tests precede their implementation; verify failures are the intended
missing behavior, not unrelated environment errors. Validate each story locally
before moving on. MVP is US1 configuration/status, not deployable remote transport.

Parallel examples once prerequisites pass: US1 T005/T006; US2 independent local
socket cases versus read-only contract inspection; US3 independent pytest cases;
US4 registry tests versus documentation draft. These identify work independence,
not authority to spawn implementation agents. Optional auto-commit hooks disabled
by repository git configuration. Never stage the owner's original roadmap ZIP.

## Requirement coverage

| Requirements | Tasks |
|---|---|
| FR001–002 | T005–T009,T027 |
| FR003–004 | T011–T015,T017,T020 |
| FR005–006 | T002–T004,T013–T014,T017–T018 |
| FR007–008 | T008,T012,T015–T018 |
| FR009 | T017–T019 |
| FR010 | T006,T008–T009,T028 |
| FR011 | T007,T016,T021–T023 |
| FR012 | T010,T014,T020 |
| FR013–014 | T007–T011,T019,T022 |
| FR015 | T013–T015,T023–T026 |
| FR016 | T014,T020–T022 |
| FR017 | T005–T007,T021–T023 |
| FR018 | T027 |
| FR019–020 | T001,T026–T031 |
| FR021–024 | T033–T036,T028 |
| FR025 | T037,T039 |
| FR026 | T036,T040 |
| SC001 | T005–T011 |
| SC002–003 | T012–T016,T028 |
| SC004 | T017–T020,T028 |
| SC005 | T006,T008,T021–T022,T028 |
| SC006 | T026 |
| SC007 | T005–T007,T021–T023 |
| SC008 | T027–T031 |
