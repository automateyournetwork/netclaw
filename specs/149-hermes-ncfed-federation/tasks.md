# Tasks: Hermes NCFED federation

**Input**: spec.md, plan.md, research.md, data-model.md and contracts/.
**Authorization**: Owner requested plan through implementation with analysis and no further clarification. Tests are required by the specification acceptance criteria.

[P] denotes an independent file task, not permission to bypass dependencies. Research used agents as required by the planning skill; implementation remains owned by the primary agent.

## Phase 1: Setup

**Goal / independent validation**: Establish reproducible fixtures and preserve the spec148 baseline.

- [x] T001 Record selected toolchain and isolated real-Hermes fixture prerequisites in tests/n2n/README.md and specs/149-hermes-ncfed-federation/verification.md
- [x] T002 [P] Add runtime/card, trust-scope and uncertainty regression fixtures in tests/n2n/test_hermes_runtime_149.py and tests/n2n/test_execution_context_149.py

## Phase 2: Foundations

**Goal / independent validation**: Immutable installation/context and protected runtime are prerequisites to all execution journeys.

- [x] T003 Implement canonical selected-installation resolution, private ownership fence and safe harness projection in mcp-servers/protocol-mcp/bgp/federation/runtime.py
- [x] T004 Add durable execution context, dispatch/usage state and deduplication migrations in mcp-servers/protocol-mcp/bgp/federation/manager.py and tasks.py
- [x] T005 Implement installation-bound private execution permits, one-use operator effects and owned handles in mcp-servers/protocol-mcp/bgp/federation/execution.py
- [x] T006 Add isolated federation namespace and immutable admission scope to mcp-servers/hermes-hud-mcp/ledger.py, bridge.py and federation_server.py while preserving HUD contracts
- [x] T007 Implement frozen receiver tool profiles and per-dispatch authorization in mcp-servers/hermes-hud-mcp/policy.py, protected_agent.py and hermes_api.py
- [x] T008 Implement official private MCP client and managed companion lifecycle in mcp-servers/protocol-mcp/bgp/federation/hermes_runtime.py

## Phase 3: US1 — Selected installation startup

**Goal / independent validation**: Independently start/status/restart custom Hermes home without OpenClaw or cross-installation state.

- [x] T009 [US1] Test custom-home, descriptor-only, identity mismatch and owned lifecycle in tests/n2n/test_hermes_lifecycle_149.py and tests/unit/test_cli_environment.py
- [x] T010 [US1] Wire selected runtime dispatch with explicit unsupported ingress and no fallback in mcp-servers/protocol-mcp/bgp/federation/gateway.py and negotiate.py
- [x] T011 [US1] Bind daemon/CLI/peering launch state, endpoints and owned stop to the installation in scripts/netclaw, scripts/peering-launch.py, scripts/peering-setup.sh and mcp-servers/protocol-mcp/bgp-daemon-v2.py
- [x] T012 [US1] Extend existing component private-server/interpreter setup in config/installer-access.json and scripts/lib/install-steps.sh; preserve repeated installation

## Phase 4: US2 — Hermes Border internal delegation

**Goal / independent validation**: Discover, route, invoke tool, delegate skill and retrieve actual attributed member result.

- [x] T013 [US2] Test actual internal transport and bounded scoped operator calls in tests/n2n/test_hermes_internal_149.py
- [x] T014 [US2] Qualify scoped operator n2n MCP calls and broker credentials in mcp-servers/hermes-hud-mcp/federation_tools.py, policy.py, config/hermes-hud-tool-policy.json and mcp-servers/n2n-mcp/server.py
- [x] T015 [US2] Wire Border routing/delegation, origin preservation, post-wait scope validation and durable outbound intent in mcp-servers/protocol-mcp/bgp/federation/service.py and invocation.py
- [x] T016 [US2] Use selected qualified registrations and official MCP client with cleanup for direct Hermes tools in mcp-servers/protocol-mcp/bgp/federation/invocation.py
- [x] T017 [US2] Preserve selected model/tool/harness metadata and qualification states in mcp-servers/protocol-mcp/bgp/federation/inventory.py and member_inventory.py

## Phase 5: US3 — Mixed and all-Hermes members

**Goal / independent validation**: All four Border/member runtime combinations enroll, discover and execute within member scope.

- [x] T018 [US3] Test scoped member configuration/environment and duplicate launch protection in tests/n2n/test_hermes_members_149.py
- [x] T019 [US3] Provision private Hermes member homes, qualified skills and least-privilege credentials in scripts/in2n-member-home.py, in2n-profiles.py and in2n-migrate.py
- [x] T020 [US3] Launch selected member runtime with fresh scoped environment/lock and companion ownership in scripts/in2n-member.py
- [x] T021 [US3] Generate installation-bound services/interpreters and correct unmanaged fallback in scripts/in2n-services.py and scripts/systemd/netclaw-mesh.service
- [x] T022 [US3] Enforce selected-runtime production posture and exact protected paths in mcp-servers/protocol-mcp/bgp/federation/controls.py and posture.py
- [x] T023 [US3] Integrate member receiver profile, empty-scope denial and trusted origin in mcp-servers/protocol-mcp/bgp/federation/service.py

## Phase 6: US4 — Bidirectional external federation

**Goal / independent validation**: Both external pair types support inventory, isolated contextual chat, tools and async skills in both directions.

- [x] T024 [US4] Test two-peer/two-session isolation and real receiver qualification in tests/n2n/test_hermes_external_149.py and test_chat_session_boundaries.py
- [x] T025 [US4] Bind external skill execution to per-owner/per-task context and receiver policy in mcp-servers/protocol-mcp/bgp/federation/invocation.py
- [x] T026 [US4] Bind chat execution to installation/peer/session and conversation-only receiver policy in mcp-servers/protocol-mcp/bgp/federation/chat.py
- [x] T027 [US4] Verify additive harness/card and request-deduplication compatibility with old peers in tests/n2n/test_inventory.py and test_hermes_runtime_149.py

## Phase 7: US5 — Authorization and approval control

**Goal / independent validation**: Zero dispatches for forged scope, stale/reused approval, revocation, unsafe target or external privilege promotion.

- [x] T028 [US5] Test exact approval consumption and revocation during pending execution in tests/n2n/test_invocation_readmission.py and test_execution_context_149.py
- [x] T029 [US5] Bind/expire/consume approvals atomically with current grant and request digest in mcp-servers/protocol-mcp/bgp/federation/authorization.py and invocation.py
- [x] T030 [US5] Verify protected agent rejects native/admin tools, foreign requests, drift and unsafe targets in tests/hermes-hud/test_protected_agent.py and tests/n2n/test_execution_context_149.py
- [x] T031 [US5] Audit selected receiver/direct-tool/broker paths and close any bypass in mcp-servers/protocol-mcp/bgp/federation/execution.py, invocation.py and service.py

## Phase 8: US6 — HUD observation and recovery

**Goal / independent validation**: Selected federation works in HUD; interrupted work remains truthful and never automatically repeats.

- [x] T032 [US6] Test dispatch loss/cancel/restart/reconciliation and retained uncertainty in tests/n2n/test_hermes_recovery_149.py and test_tasks.py
- [x] T033 [US6] Complete task cancellation, owner-bound result/provenance, reconciliation and retention behavior in mcp-servers/protocol-mcp/bgp/federation/tasks.py and hermes_runtime.py
- [x] T034 [US6] Replace Hermes blanket federation denial with selected-installation readiness in ui/netclaw-visual/server.js and src/hud-server/runtime/routes.js while retaining unrelated restrictions
- [x] T035 [US6] Render safe harness/model/tools/posture/task outcomes in ui/netclaw-visual/src/dashboard/ReferenceViews.jsx, Dashboard.jsx, model.js and src/orgchart/peer-detail.js
- [x] T036 [US6] Add HUD legacy/unknown/stale/foreign-installation regression cases in ui/netclaw-visual/src/dashboard/hermes-ui.test.js, model.test.js and src/orgchart/peer-detail.test.js

## Phase 9: US7 — Preservation and acceptance

**Goal / independent validation**: Repeated installation/upgrade/rollback preserve owner state and core runtime combinations have actual execution evidence.

- [x] T037 [US7] Test populated selected homes and rollback/preservation in tests/unit/test_n2n_install_preservation.py and tests/n2n/test_hermes_lifecycle_149.py
- [x] T038 [US7] Build real pinned-Hermes controlled-provider NCFED acceptance harness in tests/n2n/hermes_acceptance_149.py, including runtime matrix, authenticated transport, skills/tools and process faults
- [x] T039 [US7] Run actual Mac acceptance and record sanitized evidence/limitations in specs/149-hermes-ncfed-federation/verification.md and evidence/
- [ ] T040 [US7] Run required Linux/WSL host/control acceptance; if unavailable, prepare a handoff while leaving this task unchecked and retaining pending dispositions in specs/149-hermes-ncfed-federation/validation-handoff.md
- [x] T041 [US7] Run existing OpenClaw, shared knowledge/replication/edge, Hermes HUD/Canvas/Avatar and installer regressions and record results in specs/149-hermes-ncfed-federation/verification.md

## Phase 10: Polish and coherent delivery

**Goal / independent validation**: Documentation, final analysis and all required gates reflect the actual implemented/qualified scope.

- [x] T042 Update README.md, docs/HERMES-HUD.md, docs/N2N-RISK.md, docs/ietf/draft-capobianco-ncfed-00.md, SOUL.md, TOOLS.md, workspace/skills/n2n-federation/SKILL.md and .env.example for actual support and harness semantics
- [x] T043 Reconcile component declarations/reference output and run applicable checks using scripts/verify-catalog-coverage.py, scripts/verify-spec-artifacts.py and ui/netclaw-visual/package.json
- [x] T044 Draft specs/149-hermes-ncfed-federation/blog-draft.md and finalize task/evidence/analysis records with owner-authorized publication in T055, without claiming unrun host tests

## Phase 11: US8 — NetClaw Mobile with a Hermes Border

Owner expanded the current work before completion. These tasks depend on foundations and overlap backend recovery/qualification; complete before final acceptance/polish and re-run analysis.

- [x] T045 [US8] Add mobile scope/contracts and cross-artifact analysis to spec.md, plan.md, contracts/mobile.md, research.md and analysis.md
- [x] T046 [US8] Test authenticated device operator admission, cross-device denial, voice origin, reconnect and explicit attachment refusal in tests/n2n/test_hermes_mobile_149.py
- [x] T047 [US8] Implement device-bound operator scopes and protected-profile/broker support in service.py, execution.py, operator.py, hermes_runtime.py and protected_agent.py
- [x] T048 [US8] Implement owned admission reconciliation, progress, canonical/legacy task projections and cancellation requested/confirmed in tasks.py, invocation.py, service.py and edge.py
- [x] T049 [US8] Extend Flutter request persistence, task parsing, reconnect recovery and headless Siri/watch handling in lib/ncfed/edge_ask_client.dart, conversation_store.dart, turn_reconciler.dart and ask_border_headless.dart
- [x] T050 [US8] Render uncertainty/interruption/cancellation, Border harness and unavailable Hermes attachments in mobile Chat/Dashboard/capture views and native Watch/Live Activity Swift presentations with safe legacy fallback
- [x] T051 [US8] Add and run mobile unit/widget/protocol tests plus existing OpenClaw Ask Border, origin voice, attachment, progress and reconnect regressions
- [x] T052 [US8] Run actual protected Hermes/mobile acceptance for text/delegation/voice/cancel/recovery and record protocol versus simulator/physical-device evidence
- [x] T053 [US8] Produce changed mobile client build, document minimum version/build/signing/device/platform coverage and unrun tests in verification.md, mobile compatibility documentation and validation-handoff.md; owner-authorized App Store Connect/TestFlight upload; no public App Review submission or release

## Dependencies and implementation strategy

Setup → foundations → US1 → US2 → US3/US4 → US5 → US6 → US7 → polish. Shared-file tasks are sequential even when stories are conceptually separate. Security tests are introduced before their dependent implementation; no supported execution is enabled without its policy path.

MVP checkpoint is selected Hermes startup plus one scoped internal delegation; it is not completion of spec149. Continue through all external/member/card/failure/preservation requirements. Tasks that require an unavailable host remain open with evidence and a runnable handoff.

Parallel opportunities after foundations: source-independent fixtures/document review for member lifecycle and external chat can run together. Within US6, UI projection tests can run alongside backend-only recovery tests after their contracts are stable. Final independent Python/Node/artifact checks can run concurrently; inspect all results.

Total: 55 tasks. US8 remains part of this delivery; finish T045–T053 before final T039–T044 evidence closure.

- [x] T054 [US8] Verify an unused app version/build, archive all Apple bundles, validate and upload the qualified candidate to App Store Connect under the owner’s latest authorization; record receipt and processing without public release.

- [ ] T055 Update source VERSION to 1.8.0, README, changelog/release notes and create the reviewed spec149 PR; publish “Good news for Hermes users!” with all five infographics, both PR links, NetClaw/Latest indexing and public verification on automateyournetwork.com.
