# Tasks: NetClaw for Visual Studio Code

**Input**: [spec.md](spec.md), [plan.md](plan.md), [research.md](research.md), [data-model.md](data-model.md), [contracts](contracts/operator-mcp.md), [quickstart.md](quickstart.md).

**Status**: Planned only. All implementation/acceptance tasks are unchecked. Ratify the design before implementation. The owner authorized pushing this specification and a real Windows/WSL handoff, not implementing or publishing the extension.

Tests are included because the specification explicitly requires contract, security, platform, real-client and release acceptance. Write behavioral tests before dependent handlers, then run them against the real implementation. Test scaffolding alone never closes acceptance.

Paths are repository-relative. `[P]` identifies independent files runnable together only after their shared phase prerequisites. Phase order controls shared-file ownership; cross-story parallel implementation is not assumed.

## Phase 1: Setup

**Goal**: Establish the isolated extension/toolchain and qualification harness.

**Independent test**: Schemas/package scripts load in the minimum editor test runner without contacting owner services.

- [ ] T001 Create pinned workspace-extension manifest/build/test configuration in `extensions/netclaw-vscode/package.json`, `tsconfig.json` and lockfile; use VS Code ^1.102.0, TypeScript 5.9.3 and Node-compatible official SDK builds. (FR-003, FR-008, FR-039)
- [ ] T002 Create private official-SDK server package boundaries and dependency locks in `mcp-servers/netclaw-operator-mcp/package.json` and `mcp-servers/netclaw-assistant-mcp/package.json`; keep Node/Python environments isolated. (FR-039)
- [ ] T003 [P] Create synthetic installations, fake authoritative approval service and fault harness in `tests/operator/fixtures.mjs`, plus initially failing foundation behavior tests in `tests/operator/foundations.test.mjs`; forbid fixture defaults from selecting owner homes or real devices. (FR-022, FR-023, FR-036, SC-006, SC-008)
- [ ] T004 [P] Add editor/minimum-version and platform runner scaffolding in `tests/vscode/runner.mjs` and `extensions/netclaw-vscode/test/`; record candidate versions without representing fixtures as real WSL. (FR-008, FR-040, SC-001, SC-003)

**Parallel example**: T003 and T004 can be authored together after the shared prerequisites; run their acceptance after the corresponding handlers exist.

## Phase 2: Foundations

**Goal**: Make identity, authority, durability and shared domain boundaries enforceable before story handlers.

**Independent test**: Negative permission/direct-call and lost-receipt tests fail closed; real shared adapters preserve prior clients.

- [ ] T005 Define versioned strict envelopes, fixed tool/action unions, response bounds and stable errors in `mcp-servers/netclaw-operator-mcp/schemas.mjs` and `mcp-servers/netclaw-assistant-mcp/schemas.mjs` from both contracts. (FR-005, FR-036, FR-039, FR-043)
- [ ] T006 Implement authenticated installation/principal binding and opaque revisions in `ui/netclaw-visual/src/management/identity.js`; derive identity from launch context, never supplied client labels. (FR-005, FR-006, FR-044, SC-005)
- [ ] T007 Implement immutable grant propagation, per-hop target/action checks, authoritative CR validation and strict Local/Lab distinction in `ui/netclaw-visual/src/management/policy.js`; disable delegation where a runtime lacks enforceable attenuation. (FR-017, FR-022, FR-023, FR-035, FR-043, FR-044, SC-006, SC-013)
- [ ] T008 Implement SQLite admission, nonce digest uniqueness, leases, revision locks, ownership, event sequence and retained tombstones in `ui/netclaw-visual/src/management/journal.js`; test migrations and stale/expired nonces. (FR-006, FR-013, FR-020, SC-005, SC-007)
- [ ] T009 Implement independently owned workers and authoritative reconciliation in `ui/netclaw-visual/src/management/worker.js`; façade exit cannot kill services and uncertain dispatch never requeues. (FR-013, FR-021, SC-007, SC-011)
- [ ] T010 Implement shared proposal preparation/approval/verification/recovery state machine in `ui/netclaw-visual/src/management/proposals.js`; store real private baseline artifacts and redacted intent only. (FR-020, FR-022, FR-023, FR-024, FR-043, SC-006, SC-008)
- [ ] T011 Add installation-specific GAIT sessions, bounded redaction/evidence access and fail-closed audit in `ui/netclaw-visual/src/management/evidence.js`; isolate root/sticky file and never rewrite history. (FR-024, FR-029, FR-036, FR-038, SC-008)
- [ ] T012 Implement fixed private MCP façade and safe launchers in `mcp-servers/netclaw-operator-mcp/server.mjs` and `scripts/netclaw-operator.mjs`; stdio-only output, verified SSH path quoting, no shell/URL dispatcher. (FR-005, FR-007, FR-039, SC-005)
- [ ] T013 Extract shared non-listening domain entry points from `ui/netclaw-visual/server.js` and runtime adapters; route existing managed-resource writes through shared revision/ownership locks without changing unrelated routes. (FR-020, FR-039, SC-011)
- [ ] T014 Run foundation denial, CR withdrawal, grant spoofing/nested delegation, audit loss, database/crash/replay and cross-client fixtures in `tests/operator/foundations.test.mjs`; fix failures before story dispatch is enabled. (FR-022, FR-023, FR-024, FR-036, FR-043, FR-044, SC-005, SC-006, SC-007, SC-008, SC-013)

**Parallel example**: Keep this phase sequential because its tasks share adapters, manifests or acceptance dependencies; fixture drafting may be prepared independently but does not close a task.

## Phase 3: US1 — Install and connect (P1)

**Goal**: Bind native navigation to the right existing installation.

**Independent test**: Clean VSIX candidate connects two real reference targets and isolates state; Restricted Mode and missing prerequisites never dispatch.

- [ ] T015 [P] [US1] Add connection/identity/SSH/WSL mismatch, no-folder/multi-root and Restricted Mode contract tests in `tests/vscode/connections.test.mjs`. (FR-004, FR-005, FR-006, FR-007, FR-008, FR-035, SC-005)
- [ ] T016 [P] [US1] Add multiwindow/profile storage, stale-response and mobile-logo manifest tests in `extensions/netclaw-vscode/test/profiles.test.ts`. (FR-002, FR-003, FR-006, SC-005)
- [ ] T017 [US1] Implement verified local/SSH transport and explicit WSL reopen flow in `extensions/netclaw-vscode/src/connection/connect.ts`; show backend compatibility/prerequisite guidance without installation. (FR-004, FR-005, FR-007, FR-008)
- [ ] T018 [US1] Implement nonsecret host/principal/profile storage and immutable connection generations in `extensions/netclaw-vscode/src/state/profiles.ts`; never sync credentials or retarget running requests. (FR-004, FR-006, SC-005)
- [ ] T019 [US1] Implement native explorer/status/output/commands and trust handlers in `extensions/netclaw-vscode/src/extension.ts` and `src/views/overview.ts`; typed resource identity and bounded partial failure. (FR-003, FR-014, FR-035, FR-037)
- [ ] T020 [US1] Copy the actual mobile PNG and derive a theme-safe Activity Bar mark in `extensions/netclaw-vscode/resources/`; wire icon and walkthrough contributions in `package.json`. (FR-002, FR-003, FR-040, SC-010)
- [ ] T021 [US1] Execute US1 minimum-editor/local/remote connection scenarios and capture measured onboarding/isolation in `specs/150-vscode-extension/evidence/connections.md`; do not count future WSL acceptance early. (FR-005, FR-008, FR-035, SC-001, SC-005)

**Parallel example**: T015 and T016 can be authored together after the shared prerequisites; run their acceptance after the corresponding handlers exist.

## Phase 4: US2 — Chat, Canvas and Avatar (P1)

**Goal**: Drive owned NetClaw work and preserve saved investigations.

**Independent test**: Qualified requests work on both harnesses, explicit context and view switches behave correctly, reload resumes without resend.

- [ ] T022 [P] [US2] Add owned chat/context/stream/cancel/uncertainty tests in `tests/operator/conversations.test.mjs` using both runtime adapters. (FR-009, FR-010, FR-012, FR-013, FR-017, SC-007)
- [ ] T023 [P] [US2] Add hostile webview and versioned Canvas preservation tests in `extensions/netclaw-vscode/test/rich-views.test.ts`. (FR-011, FR-012, FR-036, SC-008, SC-011)
- [ ] T024 [US2] Implement owned conversations and durable OpenClaw admission/recovery in `ui/netclaw-visual/src/management/conversations.js`; preserve Hermes ledger, enforced grant propagation and qualified model/effort limits. (FR-009, FR-010, FR-013, FR-017, FR-043, SC-007)
- [ ] T025 [US2] Implement CSP-restricted typed webview bridge in `extensions/netclaw-vscode/src/webview/bridge.ts`; bind every message to view and installation generation, validate links and deny direct HUD networking. (FR-036, FR-038, SC-008)
- [ ] T026 [US2] Implement chat/draft/selected-context review and sourced events in `extensions/netclaw-vscode/src/views/chat.ts` and `src/commands/context.ts`; core chat works without Copilot. (FR-009, FR-010, FR-012, FR-013)
- [ ] T027 [US2] Adapt existing Canvas and Avatar into `extensions/netclaw-vscode/webview/` with explicit versioned import/export and native harness navigation; implement `src/views/canvas.ts` and `avatar.ts` without implicit sends. (FR-011, FR-012, FR-017, SC-011)
- [ ] T028 [US2] Run real qualified OpenClaw/Hermes read-only conversations, editor reload and saved-work preservation; record provider mode and results in `specs/150-vscode-extension/evidence/conversations.md`. (FR-009, FR-010, FR-011, FR-013, SC-003, SC-007, SC-011)

**Parallel example**: T022 and T023 can be authored together after the shared prerequisites; run their acceptance after the corresponding handlers exist.

## Phase 5: US3 — Standalone, Risk and federation (P1)

**Goal**: Operate the existing estate with accurate trust/capability boundaries.

**Independent test**: Standalone, mixed/all-Hermes internal and external relationships support qualified work and refuse unauthorized lifecycle/peer actions.

- [ ] T029 [P] [US3] Add internal/external capability, stale/legacy card and exact-action denial tests in `tests/operator/federation.test.mjs`. (FR-014, FR-015, FR-016, FR-017, SC-003, SC-006)
- [ ] T030 [US3] Implement fixed member/peer inventory, existing-estate lifecycle/peering proposals and qualified delegation in `ui/netclaw-visual/src/management/federation.js`; enforce grants at existing NCFED brokers. (FR-014, FR-015, FR-016, FR-017, FR-043)
- [ ] T031 [US3] Implement Border/member/edge/advisor tree and per-Claw inspectors in `extensions/netclaw-vscode/src/views/estate.ts`; distinguish advertisement, installation and verified tool execution. (FR-003, FR-014, FR-015, FR-017)
- [ ] T032 [US3] Implement external peer/trust/conversation/tool/skill workflows in `extensions/netclaw-vscode/src/views/peers.ts`, routing mutations through proposal review and preserving origin/evidence. (FR-016, FR-022, FR-024)
- [ ] T033 [US3] Run all four internal runtime pairs and both-direction H/H,H/O external plus O/O regression in `tests/vscode/federation-acceptance.mjs`; record actual host/provider/tool qualification separately. (FR-016, FR-017, SC-003)
- [ ] T034 [US3] Record reference estate results and outstanding per-host gates in `specs/150-vscode-extension/evidence/federation.md`; require Linux/WSL matrix and spec149 host-control dependency before release. (FR-008, FR-017, FR-040, SC-003)

**Parallel example**: Keep this phase sequential because its tasks share adapters, manifests or acceptance dependencies; fixture drafting may be prepared independently but does not close a task.

## Phase 6: US4 — Settings and runtime operation (P1)

**Goal**: Manage supported configuration and owned services with real verification.

**Independent test**: Synthetic secret updates preserve unrelated data, conflict correctly, and show saved/effective/restart/rollback outcomes.

- [ ] T035 [P] [US4] Add env keep/replace/clear, concurrent revision, file ownership/symlink and legacy credential migration tests in `tests/operator/configuration.test.mjs`. (FR-018, FR-019, FR-020, FR-036, SC-008)
- [ ] T036 [P] [US4] Add service ownership, active-work impact, stop/restart failure and extension-disconnect preservation tests in `tests/operator/lifecycle.test.mjs`. (FR-007, FR-021, SC-007, SC-011)
- [ ] T037 [US4] Implement typed configuration/budget/integration transactions in `ui/netclaw-visual/src/management/configuration.js`; preserve unmanaged bytes and normalize legacy credential references through reviewed shared launchers with recovery. (FR-018, FR-019, FR-020, FR-028, SC-008)
- [ ] T038 [US4] Implement narrow installation-owned service controls and runtime/role changes in `ui/netclaw-visual/src/management/lifecycle.js` and `runtime.js`; no installer scripts, unit deletion or process-name killing. (FR-007, FR-018, FR-020, FR-021, SC-011)
- [ ] T039 [US4] Implement settings/provider/harness/budget/mode forms and impact review in `extensions/netclaw-vscode/src/views/settings.ts`; selection alone never switches backend runtime. (FR-018, FR-020, FR-021)
- [ ] T040 [US4] Implement environment inventory, explicit transient secret inputs and redacted revision-aware review in `extensions/netclaw-vscode/src/views/configuration.ts`; never persist secret drafts in editor state. (FR-019, FR-020, FR-036, SC-008)
- [ ] T041 [US4] Run settings/service transactions with real postcondition/rollback observations in controlled installs and record `specs/150-vscode-extension/evidence/configuration.md`; retain failures/unknowns. (FR-007, FR-018, FR-020, FR-021, SC-006, SC-008, SC-011)

**Parallel example**: T035 and T036 can be authored together after the shared prerequisites; run their acceptance after the corresponding handlers exist.

## Phase 7: US5 — Approval, GAIT and security (P1)

**Goal**: Make exact authority, audit and actual enforcement inspectable.

**Independent test**: Unapproved production and out-of-scope lab work is denied; supported synthetic approved actions retain complete evidence.

- [ ] T042 [P] [US5] Add exact Terminal Intent Local/Lab, read-only collector, GAIT root and guard/confinement enforcement cases in `tests/operator/security.test.mjs`. (FR-022, FR-023, FR-024, FR-025, FR-026, SC-006)
- [ ] T043 [US5] Implement owned durable Terminal Intent adapter in `ui/netclaw-visual/src/management/intent.js`; preserve designated endpoints/API-created record/real artifacts/APPLY phase, never infer approval from questions. (FR-013, FR-022, FR-023, SC-006, SC-007)
- [ ] T044 [US5] Implement security scans/rules/events and separate DefenseClaw/OpenShell/host-posture adapters in `ui/netclaw-visual/src/management/security.js`; permitted settings use narrow transactions, no installer wrappers. (FR-025, FR-026, FR-039)
- [ ] T045 [US5] Implement Operations proposal/approval/verification view and append-only GAIT browser in `extensions/netclaw-vscode/src/views/operations.ts` and `gait.ts` with redacted export. (FR-022, FR-023, FR-024, FR-029, SC-006)
- [ ] T046 [US5] Implement distinct effective/observe-only/degraded/disabled/unavailable security and OpenShell controls in `extensions/netclaw-vscode/src/views/security.ts` and `openshell.ts`. (FR-025, FR-026, FR-037)
- [ ] T047 [US5] Run production-denial, authoritative approval withdrawal, lab-scope and rollback-failure qualification and record `specs/150-vscode-extension/evidence/security.md`; leave failed CRs unresolved and report escalation. (FR-022, FR-023, FR-024, FR-025, FR-026, SC-006)

**Parallel example**: Keep this phase sequential because its tasks share adapters, manifests or acceptance dependencies; fixture drafting may be prepared independently but does not close a task.

## Phase 8: US9 — Copilot, Claude Code and Codex (P1)

**Goal**: Allow scoped natural-language inspection, delegation and proposals in each named client.

**Independent test**: Actual clients complete owned workflows and fail direct/self-approval, grant escape, revocation and cross-client cases.

- [ ] T048 [P] [US9] Add assistant direct-method denial, cross-client ownership, nested grant escape and disclosure redaction tests in `tests/assistant-clients/contract.test.mjs`. (FR-041, FR-042, FR-043, FR-044, SC-005, SC-008, SC-013)
- [ ] T049 [US9] Implement assistant-only façade and fixed launcher in `mcp-servers/netclaw-assistant-mcp/server.mjs` and `scripts/netclaw-assistant.mjs`; expose only the seven tools and enforce grant on every call. (FR-042, FR-043, FR-044, SC-013)
- [ ] T050 [US9] Implement reviewed client grants, backend .env credential references, bounded disclosure/expiry/revocation and in-flight handling in `ui/netclaw-visual/src/management/clients.js`; no plaintext credential journal/config. (FR-038, FR-041, FR-042, FR-043, FR-044, SC-005, SC-008)
- [ ] T051 [US9] Implement opt-in stable Copilot MCP provider in `extensions/netclaw-vscode/src/clients/copilot.ts`; immutable installation+grant definitions, side-effect-free discovery, resolve-time checks and client policy errors. (FR-035, FR-041, FR-044, SC-013)
- [ ] T052 [US9] Implement reviewed version-aware Claude Code/Codex stdio setup/export in `extensions/netclaw-vscode/src/clients/terminal.ts`; preserve unrelated config, explicit host paths and editor-independent operation. (FR-042, FR-044, SC-013)
- [ ] T053 [US9] Implement client grant/disclosure review and proposal status in `extensions/netclaw-vscode/src/views/clients.ts`; distinguish external assistant and NetClaw inference/costs, deny self-approval. (FR-041, FR-042, FR-043, FR-044)
- [ ] T054 [US9] Run actual Copilot, Claude Code and Codex inventory/delegation/proposal/denial/revocation/lost-response tests in `tests/assistant-clients/acceptance.mjs` on both harnesses, including real WSL and Remote SSH. (FR-008, FR-041, FR-042, FR-043, FR-044, SC-013)
- [ ] T055 [US9] Document exact verified client commands, versions, grants, disclosure and same-UID limitations in `docs/VSCODE-ASSISTANTS.md` and evidence in `specs/150-vscode-extension/evidence/assistant-clients.md`. (FR-034, FR-038, FR-041, FR-042, FR-043, FR-044, SC-013)

**Parallel example**: Keep this phase sequential because its tasks share adapters, manifests or acceptance dependencies; fixture drafting may be prepared independently but does not close a task.

## Phase 9: US6 — Usage, integrations, logs and network (P2)

**Goal**: Expose useful operational evidence with its real scope.

**Independent test**: Known fixtures reconcile exactly while stale/missing/malformed sources remain explicit.

- [ ] T056 [P] [US6] Add exact usage totals/gaps, source distinctions and bounded/redacted log tests in `tests/operator/observability.test.mjs`. (FR-027, FR-028, FR-029, FR-030, SC-008, SC-009)
- [ ] T057 [US6] Implement usage and diagnostic projections through `ui/netclaw-visual/src/management/evidence.js`; expose local OpenClaw and owned Hermes scope without invented aggregation. (FR-027, FR-029, SC-009)
- [ ] T058 [US6] Implement Tokenomics/integration inventory and supported configuration navigation in `extensions/netclaw-vscode/src/views/tokenomics.ts` and `integrations.ts`. (FR-015, FR-027, FR-028, SC-009)
- [ ] T059 [US6] Implement logs/diagnostic preview/export and network/topology/intent entry in `extensions/netclaw-vscode/src/views/logs.ts` and `network.ts`; label configured/live/historical/simulated/federation sources. (FR-023, FR-029, FR-030, FR-038, SC-008)
- [ ] T060 [US6] Run source/cost reconciliation, unavailable integration and topology provenance acceptance; record `specs/150-vscode-extension/evidence/observability.md`. (FR-027, FR-028, FR-029, FR-030, SC-009)

**Parallel example**: Keep this phase sequential because its tasks share adapters, manifests or acceptance dependencies; fixture drafting may be prepared independently but does not close a task.

## Phase 10: US7 — Knowledge, advice, mobile and help (P2)

**Goal**: Complete the supporting HUD workspace inside the editor.

**Independent test**: Selected RAG upload retrieves citations, memory validity/advice ownership stay visible, mobile consent and help paths work.

- [ ] T061 [P] [US7] Add RAG selection/indexing, memory validity, Jev ownership and mobile consent/unsupported harness tests in `tests/operator/workspace.test.mjs`. (FR-012, FR-031, FR-032, FR-033, FR-034)
- [ ] T062 [US7] Implement bounded RAG/memory/GCF/meeting/assessment/mobile adapters in `ui/netclaw-visual/src/management/workspace.js`; use existing qualified tools, no workspace ingest or new device/vendor execution. (FR-012, FR-031, FR-032, FR-033, FR-039)
- [ ] T063 [US7] Implement RAG/knowledge collection/context views in `extensions/netclaw-vscode/src/views/rag.ts` and `knowledge.ts` with citations, progress/errors and recorded validity. (FR-012, FR-031)
- [ ] T064 [US7] Implement Science Officer and mobile/edge views in `extensions/netclaw-vscode/src/views/science.ts` and `mobile.ts`; advice-only ownership, budgets, enrollment versus connectivity and explicit consent. (FR-014, FR-032, FR-033)
- [ ] T065 [US7] Implement searchable local documentation and version/context help in `extensions/netclaw-vscode/src/views/documentation.ts`, including existing guides and validated external navigation. (FR-034, FR-036)
- [ ] T066 [US7] Execute all supporting-domain positive/denial cases and record `specs/150-vscode-extension/evidence/workspace.md`; do not claim Hermes media or physical-device qualification from rendering a control. (FR-031, FR-032, FR-033, FR-034, SC-002)

**Parallel example**: Keep this phase sequential because its tasks share adapters, manifests or acceptance dependencies; fixture drafting may be prepared independently but does not close a task.

## Phase 11: US8 — Distribution preparation (P2)

**Goal**: Prepare a real distributable release; public completion depends on final gates.

**Independent test**: Clean candidate installation/update/preservation and package inspection pass before authorized publication.

- [ ] T067 [US8] Confirm authorized publisher/extension ID and select release/backend versions in `extensions/netclaw-vscode/package.json` and `docs/VSCODE-COMPATIBILITY.md`; record actual API/OS/client/harness contract support. (FR-001, FR-008, FR-040, SC-003, SC-012)
- [ ] T068 [US8] Create Marketplace README/changelog/license/privacy/screenshots/walkthrough and explicit package allowlist in `extensions/netclaw-vscode/README.md`, `CHANGELOG.md`, `LICENSE` and `.vscodeignore`. (FR-001, FR-002, FR-034, FR-038, FR-040, SC-012)
- [ ] T069 [US8] Add packaging/release artifact and synthetic-secret inspection automation in `tests/vscode/package.test.mjs` and `.github/workflows/vscode-extension.yml`; do not auto-publish from an unapproved branch push. (FR-001, FR-036, FR-038, FR-040, SC-008, SC-012)
- [ ] T070 [US8] Build matching VSIX and run clean install/previous-candidate upgrade/disable/uninstall/rollback, retaining backend processes/data; record `specs/150-vscode-extension/evidence/package.md`. (FR-001, FR-007, FR-040, SC-001, SC-008, SC-011, SC-012)

**Parallel example**: Keep this phase sequential because its tasks share adapters, manifests or acceptance dependencies; fixture drafting may be prepared independently but does not close a task.

## Phase 12: Cross-cutting qualification, coherence and authorized publication

**Goal**: Finish every domain and host gate, then observe actual public installation.

**Independent test**: All required rows pass with exact evidence; otherwise release remains incomplete.

- [ ] T071 Add private operator/assistant components to `scripts/lib/catalog.sh`, `scripts/lib/install-steps.sh` and `scripts/verify-catalog-coverage.py`; owner installs through normal NetClaw updates, never the extension. Keep private operator out of `config/openclaw.json` and document registration applicability. (FR-007, FR-039, FR-040)
- [ ] T072 Complete HUD integration visibility and architecture/count/setup updates in `ui/netclaw-visual/src/dashboard/model.js`, `README.md`, `SOUL.md`, `TOOLS.md`, `.env.example`, both new MCP READMEs and `workspace/skills/netclaw-operator/SKILL.md`; document secret-free private setup and operations. (FR-003, FR-028, FR-034, FR-039, FR-040)
- [ ] T073 Run 23-domain coverage, keyboard/theme, hostile-content and measured inventory p95 acceptance in `tests/vscode/workbench-acceptance.mjs`; summarize exact SC-004/010 results in `specs/150-vscode-extension/evidence/workbench.md`. (FR-003, FR-036, FR-037, SC-002, SC-004, SC-008, SC-010)
- [ ] T074 Run applicable existing HUD/Canvas/mobile/CLI/federation/runtime suites and catalog/spec artifact checks in declared isolated environments; record commands/counts/limits in `specs/150-vscode-extension/evidence/regression.md`. (FR-039, FR-040, SC-003, SC-011)
- [ ] T075 Execute owner-machine read-only WSL baseline and, after implementation/authorized test scope, real E3/E8 and WSL runtime/client/fault gates per `specs/150-vscode-extension/windows-wsl-handoff.md`; record separate `evidence/wsl-baseline.md` and `evidence/wsl-acceptance.md`, resolving spec149 Linux/WSL dependencies. (FR-008, FR-040, FR-041, FR-042, FR-043, FR-044, SC-001, SC-003, SC-005, SC-006, SC-007, SC-008, SC-011, SC-013)
- [ ] T076 Execute remaining E1/E2/E4/E5/E6/E7 native and Remote SSH minimum/current-editor matrix and record `specs/150-vscode-extension/evidence/platforms.md`; require real named-client/harness results and preserve unrun rows. (FR-008, FR-017, FR-040, SC-001, SC-003, SC-005, SC-007, SC-013)
- [ ] T077 Reconcile all 57 requirements and 23 domain rows against actual evidence in `specs/150-vscode-extension/verification.md`; draft `docs/releases/netclaw-vscode-announcement.md` locally for owner review and complete support/recovery docs in `docs/VSCODE.md`. (FR-034, FR-038, FR-040, SC-002, SC-012)
- [ ] T078 After all gates and explicit release authorization, publish the approved VSIX and matching download through the selected publisher; record URL/version/digests and actual clean Marketplace install/connection in `specs/150-vscode-extension/evidence/marketplace.md`. (FR-001, FR-002, FR-040, SC-012)
- [ ] T079 Close delivery only after review of complete evidence; update `specs/150-vscode-extension/tasks.md` honestly and record final GAIT summary plus sanitized release/remaining-limitations handoff in `specs/150-vscode-extension/verification.md`. (FR-024, FR-040, SC-012)

**Parallel example**: Keep this phase sequential because its tasks share adapters, manifests or acceptance dependencies; fixture drafting may be prepared independently but does not close a task.

## Dependencies and checkpoints

Setup → Foundations → US1 → US2 → US3 → US4 → US5 → US9 → US6 → US7 → US8 preparation → cross-cutting qualification → authorized publication.

- US1 depends only on foundations and is the suggested internal MVP checkpoint: real authenticated read-only connection/navigation. It is not the full requested product or a public-release completion.
- US2 reuses US1 binding; US3 adds federation on owned requests; US4 adds managed settings/lifecycle. Their story tests can use synthetic fixtures but production claims require real qualification.
- US5 completes the Operations/security frontend over foundational policy before US9 exposes assistant proposals. US9 depends on US2/3 delegation, US4 change schemas and US5 human review. No assistant registration before permission propagation passes.
- US6/7 complete all remaining HUD domains. US8 produces distributable candidates after features exist; publication waits for every cross-cutting gate.
- The read-only WSL baseline may be collected now as explicitly authorized handoff preparation. The final WSL task remains unchecked until actual extension/client/fault acceptance passes. Do not treat that early baseline as a dependency on building the extension.
- Runtime qualification, authoritative approval, owner-designated disruptive test scope, enabled named-client accounts and publisher credentials are concrete execution prerequisites. Record a blocked result where absent; do not waive the gate or invent success.

## Implementation strategy

Deliver small story checkpoints with real behavioral evidence, preserve the existing clients at each shared-adapter change, and broaden qualification when the related feature is ready. All nine stories and all domain rows remain required for the first full release. Spec149 Linux/WSL gaps and actual public Marketplace installation are mandatory release dependencies.

## Counts and traceability

79 tasks; 13 explicitly parallel task entries. All unchecked. See [traceability.md](traceability.md) for the requirement-to-task index.

| Group | Tasks |
|---|---|
| Setup | 4 |
| Foundations | 10 |
| US1 | 7 |
| US2 | 7 |
| US3 | 6 |
| US4 | 7 |
| US5 | 6 |
| US9 | 8 |
| US6 | 5 |
| US7 | 6 |
| US8 | 4 |
| Cross-cutting qualification, coherence and authorized publication | 9 |


## Read-only WSL baseline — 2026-10-10

The authorized baseline portion of T075 is recorded in [evidence/wsl-baseline.md](evidence/wsl-baseline.md).
Actual Windows VS Code/WSL, existing owner Risk and separate Hermes status were observed.
Running-backend identity/version compatibility and Node25, missing management implementation,
spec149 T040 and real client/platform qualification remain prerequisites. No implementation,
provider execution or disruptive acceptance was performed. **T075 and all other task
checkboxes remain unchecked**; the baseline is not E3/E8 or extension acceptance.
