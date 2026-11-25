# Tasks: IDE Installer — Spec153

Input: `specs/153-ide-installer/{spec,plan,research,data-model,quickstart}.md` and `contracts/`. Tests are explicitly requested. Milestone order follows the supplied plan; story labels preserve independent slices within milestones. Every story is required.

Format: `- [ ] Tnnn [USn] action with path`. `[P]` is omitted for shared-file implementation; research parallelism is complete. Different independent fixture files may be developed concurrently after their dependencies, but this does not authorize extra agents.

Owner sequencing amendment (2026-10-18): [MAC-COMPLETION.md](MAC-COMPLETION.md) fixes the Mac exit boundary. Finish Mac before executing the held WSL handoff; WSL then tests smoke/platform differences, followed by Mac regression and human rehearsal. The original **84 tasks** remain the denominator. T081 has separate Mac and WSL evidence; T083 separates synthetic engineering checks from the final human walkthrough.

## M0 — Setup and design foundation

Prerequisite for all code. Independent check: sixteen research decisions, schemas/contracts, five decisions and constitution mapping agree. Owner authorized progression after clean analysis.

- [x] T001 Preserve source inputs and five clarifications; reconcile workflow and scope in specs/153-ide-installer/spec.md and plan.md.
- [x] T002 Complete research, data model, schemas, protocol/broker/skill/preset contracts and fixture quickstart under specs/153-ide-installer/.
- [x] T003 Record prospective XI draft and current-rule coherence decisions in specs/153-ide-installer/constitution-amendment.md; update AGENTS.md context without weakening rules.
- [x] T004 Run read-only cross-artifact analysis, remediate every finding, and record clean re-analysis in specs/153-ide-installer/analysis.md before code changes.

## M1 — US11 canonical catalog (P1)

Independent check: all 110 components/237 real skills/nine profiles and registered/external integrations have explicit dispositions; shell listing and profiles match baseline; cards/settings/links/joins are complete.

- [x] T005 [US11] Capture historical catalog/profile output and inventory in tests/fixtures/setup/catalog-baseline.json; add completeness/parity/phantom-ID tests in tests/test_setup_catalog.py.
- [x] T006 [US11] Author evidence-backed components and harness/provider/channel/shape/security choice settings/platform/effect/verification metadata in config/components/catalog.json and schema.json; every field has exact consumer provenance and conditions.
- [x] T007 [US11] Resolve server/card/skill/member-profile joins, Catalyst Center paths and external/no-install dispositions in config/components/catalog.json, ui/netclaw-visual/mcp-configuration.js and scripts/lib/install-steps.sh.
- [x] T008 [US11] Generate 237 skill descriptors from real YAML front matter plus explicit joins using scripts/build-catalog.mjs; keep the deployment skill outside this inventory.
- [x] T009 [US11] Generate scripts/lib/catalog.sh preserving IDs/order/profiles/listing; add scripts/build-catalog.py --check and fix scripts/verify-catalog-coverage.py phantom ID/function coverage.
- [x] T010 [US11] Implement missing component_install_k8s or documented no-install adapter in scripts/lib/install-steps.sh and verify actual managed registration behavior.
- [x] T011 [US11] Implement schema/metadata/join/local-link checks in scripts/check-catalog-metadata.py and bounded external-link checking in scripts/check-catalog-links.py.
- [x] T012 [US11] Add PR catalog parity/changed-link checks and weekly all-link report in .github/workflows/setup-catalog.yml; run and record actual link statuses.

## M2a — US5 engine foundation (P1)

Depends M1. Independent check: fixture plan effects, classified secrets and write-ahead outcomes survive interruption without replay/false success or sibling mutation.

- [x] T013 [US5] Write strict parse/hash/schema/semantic/secret vectors and reference-validator comparisons in tests/test_setup_plan.py; include unknown fields, duplicate keys, floats, aliases and mismatched inheritance.
- [x] T014 [US5] Publish config/claw-plan.schema.json and config/setup-engine.json; implement closed stdlib validation/canonicalization/catalog semantic checks in scripts/lib/setup_plan.py.
- [x] T015 [US5] Write lock/child-survival/journal/crash/disconnect/review-mismatch tests in tests/test_setup_engine.py with injected in-process adapters and explicit fixture roots.
- [x] T016 [US5] Implement guarded paths, atomic private writes, OS resource locks and durable intent/outcome artifacts in scripts/lib/setup_state.py; retain lock ownership while children write.
- [x] T017 [US5] Implement validate/explain/apply/resume/status command/event dispatch and native/TTY review binding in scripts/setup-engine.py and scripts/lib/setup_engine.py.
- [x] T018 [US5] Implement bounded nonce-scoped secret frames, explicit child environments and guarded existing env writer reuse in scripts/lib/setup_secrets.py and scripts/write-env.py.
- [x] T019 [US5] Audit every callable component effect and implement fixed scoped bridge dispatch in scripts/lib/plan-steps.sh; prohibit implicit checkout env/global-home writes and isolate mutable source/build/prefixes. Audited 110 component dispositions and fixed scoped dispatch pass drift/isolation checks; shared-host in2n-production refuses before effects, and computer-use remains WSL-only.
- [x] T020 [US5] Add version-qualified OpenClaw/Hermes install/onboarding adapters with selected-home postconditions and visible native reconciliation in scripts/lib/setup_harness.py; reject guidance-only/no-op and unknown versions. Both pinned harnesses pass actual focused wizard and composed Risk installs, selected-home config and readiness checks; incompatible Webex/version combinations refuse before effects.
- [x] T021 [US5] Implement selected skills/config/inventory/persona/credential deployment and manifest writes in scripts/lib/setup_deploy.py, reusing existing serializers without shared mutable workspace/testbed.
- [x] T022 [US5] Implement effect-specific observe/repair/retry and explicit resume with source/target/control rechecks, pause_requested/paused/unknown distinctions in scripts/lib/setup_engine.py. Full recovery matrix passes: owned file/source repair, observed runtime/services/enrollment, explicit unknown multi-output/native outcomes, surviving-writer locks and fresh-review resume.
- [x] T023 [US5] Verify per-component failure isolation, owned-service preservation, occupied/aliased homes, port/source collisions and unchanged sibling resources in tests/test_setup_engine.py.

## M2b — US10 CLI parity (P2)

Depends M2a. Independent check: historical flags stay unchanged and a wizard-format plan validates/explains/applies identically through a controlling terminal.

- [x] T024 [US10] Add early --emit-plan/--validate-plan/--explain-plan/--plan dispatch in scripts/install.sh to scripts/lib/plan-cli.sh before legacy side effects.
- [x] T025 [US10] Implement interactive tree draft/review and private terminal secrets through the same schema/engine in scripts/lib/setup_cli.py; no --yes authority bypass.
- [x] T026 [US10] Run existing installer regressions and CLI/engine manifest/registration/readiness parity tests in tests/test_setup_cli.py.

## M3a — US1 bootstrap and Windows gate (P1)

Depends M0; engine integration after M2. Independent check: empty-window setup, exact host classification, zero-write native gate matrix and explicit stateful handoff round trip.

- [x] T027 [US1] Add setup entry command/tree primary action/walkthrough with no activation effects in extensions/netclaw-vscode/package.json, src/extension.ts and src/views/overview.ts.
- [x] T028 [US1] Implement host classifier and byte-aware read-only WSL probes/parser in extensions/netclaw-vscode/src/setup/host.ts and gate.ts, with supported-release identity checks after reopen.
- [x] T029 [US1] Implement separately reviewed WSL handoff/private non-secret resume record and public openFolder URI in extensions/netclaw-vscode/src/setup/handoff.ts.
- [x] T030 [US1] Bundle stamped runtime/preflight policies and fixed visible-terminal remedies in extensions/netclaw-vscode/src/setup/prerequisites.ts and build.mjs; preserve version-manager choice and no sudo npm.
- [x] T031 [US1] Add UTF8/UTF16/localized/error/unknown Windows fixtures, no-effect snapshots, handoff expiry/replay and full answer round trips in extensions/netclaw-vscode/test/setup-host.test.mjs.
- [x] T032 [US1] Implement bounded registered/known/user-selected installation detection and clear separate-install disclosure in extensions/netclaw-vscode/src/setup/installations.ts.

## M3b — US2 source acquisition (P1)

Depends host observation. Independent check: release/main/ref/API-failure/dirty/shared/occupied/protocol-mismatch matrix never runs unverified code or mutates another install.

- [x] T033 [US2] Write acquisition/ref/origin/proxy/error/dirty/alias/protocol fixtures in extensions/netclaw-vscode/test/setup-source.test.mjs.
- [x] T034 [US2] Implement bounded GitHub release resolution, labelled fallback tags and fixed-origin argument-vector acquisition in extensions/netclaw-vscode/src/setup/source.ts.
- [x] T035 [US2] Implement manifest/tree/commit verification and reviewed as-is reuse or unshared clean update fencing in extensions/netclaw-vscode/src/setup/source.ts.

## M4a — US3 wizard tree (P1)

Depends M1/M2/M3. Independent check: both harness/local/cloud/channel/no-channel plans, profiles and downstream invalidation without apply.

- [x] T036 [US3] Write tree/invalidation/member inheritance/settings/privacy fixtures in extensions/netclaw-vscode/test/setup-wizard.test.mjs.
- [x] T037 [US3] Implement revisioned non-secret answer model and downstream discard preview in extensions/netclaw-vscode/src/setup/plan.ts.
- [x] T038 [US3] Implement Spec151-themed accessible tree/cards/search/profile/dependency/documentation/glossary surfaces in extensions/netclaw-vscode/src/views/setup-wizard.ts and resources/setup-wizard.js/.css.
- [x] T039 [US3] Implement version-qualified harness/provider/model/channel metadata and bounded local-runtime/model discovery in scripts/lib/setup_discovery.py and extensions/netclaw-vscode/src/setup/discovery.ts.
- [x] T040 [US3] Add explicit model size/hardware/download consent, unknown-size deferral and correct Ollama/LMStudio API-mode tests in tests/test_setup_discovery.py.
- [x] T041 [US3] Wire selected settings/native secret inputs, inventory editor reuse and identity/posture files into extensions/netclaw-vscode/src/setup/secrets.ts and src/views/setup-wizard.ts.
- [x] T042 [US3] Add native exact-hash effect review, plan save/import and engine-owned minimum production-control policy in config/components/security-policy.json with refusal before apply in extensions/netclaw-vscode/src/setup/review.ts.

## M4b — US5 editor execution (P1)

Depends M2/M4a. Independent check: progress, optional failure, native-terminal cancellation, editor disconnect and explicit resume are truthful and installation-scoped.

- [x] T043 [US5] Implement engine spawn/framing/liveness/size/timeouts and native interactive step ownership in extensions/netclaw-vscode/src/setup/engine.ts. Private nonce/hash-bound terminal transport, engine-owned PTY/descendant locks and cancellation-to-unknown pass actual process tests. Adapter-specific native qualification remains T019/T020.
- [x] T044 [US5] Implement run references, sanitized progress/log UI and explicit Resume/retry with secret re-prompt in extensions/netclaw-vscode/src/setup/runs.ts and src/views/setup-wizard.ts.
- [x] T045 [US5] Add editor-owner disconnect/reload/child-survival versus independent CLI fixtures in extensions/netclaw-vscode/test/setup-runs.test.mjs.

## M5 — US6 verification, reports and multiclaw handoff (P1)

Depends M4. Independent check: every tier state and default/detailed report, authenticated Tier3 handoff and every existing management action on two distinct bindings.

- [x] T046 [US6] Write per-tier false-success/cost/message-consent and nested/private/secret export vectors in tests/test_setup_verification.py.
- [x] T047 [US6] Implement identity-bound artifacts/discovery/owned-runtime/HUD tiers 1-3 using existing readiness and management adapters in scripts/lib/setup_verify.py. Actual focused OpenClaw/Hermes and both composed Risk setups pass Tiers 1–3; native Hermes discovery supplements the protected companion without expanding its allowlist.
- [x] T048 [US6] Implement mandatory tiers 1–3 and optional bounded live-turn with native consent, per-message channel review and read-only pyATS tier adapters in scripts/lib/setup_verify.py; unavailable evidence remains unverified.
- [x] T049 [US6] Implement typed private report and default structural redacted export with separate detailed-export review in scripts/lib/setup_report.py and extensions/netclaw-vscode/src/setup/reports.ts.
- [x] T050 [US6] Wire authenticated identity review/save connection/Workbench and rerun verification in extensions/netclaw-vscode/src/extension.ts and src/setup/connections.ts.
- [x] T051 [US6] Ensure visible name/harness/home and installation-fenced config/workspace/lifecycle/caches/in-flight operations in extensions/netclaw-vscode/src/state/management.ts and src/views/overview.ts.
- [x] T052 [US6] Run same-harness and mixed pair connection switching/preservation fixtures in extensions/netclaw-vscode/test/setup-connections.test.mjs.

## M6 — US4 Shape Advisor and mixed Risk (P1)

Depends M5. Independent check: advisory small/medium/large/unknown cases; two Border harnesses, >=3 members/two providers/all four pairs, per-claw credential/services and production refusal.

- [x] T053 [US4] Write advisor/risk inheritance/profile/provider/production/secret-scope fixtures in tests/test_setup_risk.py and extensions/netclaw-vscode/test/setup-advisor.test.mjs.
- [x] T054 [US4] Implement versioned advisor policy and feasible member partition estimates in config/components/advisor.json, scripts/lib/setup_advisor.py and extensions/netclaw-vscode/src/setup/advisor.ts.
- [x] T055 [US4] Implement Border/member cards, inherited/explicit harness selection, per-member provider/profile/mode/settings and unavailable multi-host guidance in extensions/netclaw-vscode/src/views/setup-wizard.ts.
- [x] T056 [US4] Implement explicit plan materialization in scripts/lib/setup_deploy.py and scripts/lib/setup_enrollment.py, preserving legacy scripts/in2n-member-home.py behavior, using independent workspace/env/provider/config, no Border secret copying or implicit template assumptions.
- [x] T057 [US4] Implement scoped macOS launchd/WSL systemd services and ownership-safe lifecycle in scripts/lib/setup_risk.py, setup_systemd.py, setup_member_start.py and claw-setup-services.mjs; preserve the legacy scripts/in2n-services.py behavior. Actual host acceptance remains T081.
- [x] T058 [US4] Implement in-memory one-use enrollment, uncertain-outcome observation and hot/on-demand verification using existing NCFED adapters in scripts/lib/setup_risk.py, setup_enrollment.py and setup_member_start.py.
- [x] T059 [US4] Verify all four runtime pairs, per-claw providers and control gates; record unsupported protected-profile boundaries without inventing qualification in tests/test_setup_risk.py and specs/153-ide-installer/verification.md. Both actual Border harnesses with three mixed members/two provider configurations pass all four pairings and hot self-status; controlled-provider configuration is not hosted inference. Production refusal fixtures pass.

## M7a — US7 broker and assistant Q&A (P1)

Depends M4/M5; management MCP unchanged. Independent check: all clients from zero/no PATH Node, secrets absent and forbidden tool operations refused even with client auto-approval.

- [x] T060 [US7] Write broker auth/schema/replay/expiry/path/forbidden-operation tests in extensions/netclaw-vscode/test/setup-broker.test.mjs.
- [x] T061 [US7] Implement private per-window socket/registration/session lifecycle and bounded operation dispatcher in extensions/netclaw-vscode/src/setup/broker.ts.
- [x] T062 [US7] Add provisioning tools/read-only redacted projections/native UI submissions to extensions/netclaw-vscode/src/assistants/server.ts and setup.ts; expose no apply/secret-value/command operation.
- [x] T063 [US7] Wire no-connection Copilot setup definition and reviewed terminal registrations using editor execPath in extensions/netclaw-vscode/src/assistants/provider.ts.
- [x] T064 [US7] Author shared skill/source stamp and consent/collision-aware distribution in installer/assistant-skills/netclaw-install/SKILL.md and extensions/netclaw-vscode/src/setup/skills.ts.
- [x] T065 [US7] Set VSCode >=1.109/chatSkills/editor tests baseline in extensions/netclaw-vscode/package.json and scripts/editor.mjs; document compatibility migration.
- [x] T066 [US7] Run MCP initialize/list-tools/no-PATH-Node and three-client transcript parity fixtures in extensions/netclaw-vscode/test/setup-assistants.test.mjs.

## M7b — US8 intent (P2)

Depends US7. Independent check: complete/contradictory/underspecified intents for every client preserve explicit assumptions and gaps, with no silent required defaults.

- [x] T067 [US8] Add intent examples and required-choice/gap rules to installer/assistant-skills/netclaw-install/SKILL.md and docs/INTENT-PROMPTS.md.
- [x] T068 [US8] Implement intent draft assumptions/unresolved display and apply blocking in extensions/netclaw-vscode/src/setup/plan.ts and src/views/setup-wizard.ts.
- [x] T069 [US8] Add incomplete draft/missing-field and expected-plan intent matrix plus malformed/secret-bearing intent tool rejection tests in extensions/netclaw-vscode/test/setup-assistants.test.mjs.

## M8 — US9 Spec Kit deployment preset (P2)

Depends M7. Independent check: pinned CLI renders all three clients, effective templates match, canonical plan submits review and redacted report writes back outside checkout.

- [x] T070 [US9] Create stable0.7.1 preset manifest/templates/six commands and reference-only example in installer/spec-kit/netclaw-claw/.
- [x] T071 [US9] Implement native workspace selection/scaffolding/pinned Specify invocation/effective resolution checks in extensions/netclaw-vscode/src/setup/preset.ts.
- [x] T072 [US9] Implement reviewed destination/revision-safe redacted report write-back in extensions/netclaw-vscode/src/setup/preset.ts.
- [x] T073 [US9] Test each client integration, multi-client collisions, displaced command templates and no unattended dispatch in tests/test_setup_preset.py.

## M9a — US12 owned cleanup (P3)

Depends state/artifact model and M6 lifecycle. Independent check: abandoned partial install cleanup preserves preexisting/changed/shared/ambiguous files/services and reports them honestly.

- [x] T074 [US12] Write ownership/revision/symlink/shared-resource/unknown-writer cleanup tests in tests/test_setup_cleanup.py.
- [x] T075 [US12] Implement cleanup preview/hash/review/ordered owned removal and retained-artifact report in scripts/lib/setup_cleanup.py; use guarded APIs without arbitrary shell deletion.
- [x] T076 [US12] Wire separate native cleanup review and local report into extensions/netclaw-vscode/src/setup/runs.ts and src/views/setup-wizard.ts.

## M9b — Documentation, coherence and qualification

All stories remain required. Each pending environment-dependent acceptance item remains open; fixtures never mark a real-host test complete.

- [x] T077 Write docs/GETTING-STARTED-VSCODE.md, WINDOWS-WSL-PREREQUISITES.md, CLAW-PLAN.md, ASSISTANT-INSTALL.md and SPEC-KIT-CLAWS.md with actual supported behavior/limits.
- [x] T078 Update README.md, extensions/netclaw-vscode/README.md, AGENTS.md, CLAUDE.md, SOUL.md, TOOLS.md and applicable env/HUD/config touchpoints; record XI applicability matrix in specs/153-ide-installer/coherence.md.
- [x] T079 Run complete installer/extension regression and schema/catalog/engine/assistant/preset suites; audit seeded secrets/private identifiers in all artifacts and record specs/153-ide-installer/verification.md.
- [x] T080 Run isolated source-development editor preview and keyboard/light/dark/high-contrast/360px/200%-zoom checks; record screenshot observations in specs/153-ide-installer/verification.md.
- [ ] T081 Qualify the full Mac focused/Risk/CLI/wizard/three assistants/Spec, four-pair and multiclaw scope first; only afterward run WSL2 Ubuntu 24.04/26.04 smoke and platform-specific integrations, reusing platform-independent Mac evidence per MAC-COMPLETION.md; record actual evidence in specs/153-ide-installer/verification.md.
- [ ] T082 Qualify native Windows gate/handoff matrix with before/after snapshots on disposable hosts; record specs/153-ide-installer/verification.md.
- [x] T083 Run owner-authorized synthetic usability scenarios and minimal-profile timing/performance checks on Mac; defer the owner walkthrough to the final Mac return before recording (SC-002 sequencing amendment, 2026-10-18); record automated versus owner observations, rendering/progress latency and download-separated time in specs/153-ide-installer/verification.md. Track organic community feedback after release separately; do not claim recruited participants.
- [x] T084 Create local specs/153-ide-installer/milestone-draft.md and final coverage/status; update memory/2026-10-17.md and GAIT trail without publishing or touching real installations.

Follow-up after release (2026-11-25), outside the original 84-task denominator:

- [x] T085 [US6] Give the Tier 3 HUD probe a management-route timeout longer than the HUD server's 15 s `openclaw agents list` limit (other routes keep 5 s), report timeouts as `probe_timeout` instead of `probe_failed`, and retry `probe_timeout` while waiting for readiness, in scripts/lib/setup_verify.py and scripts/lib/setup_report.py; tests in tests/test_setup_verification.py. Evidence in specs/153-ide-installer/verification.md.

## Dependencies and execution strategy

M0 → M1 → M2a → M2b; M3a may use completed M0/M1 metadata, then M3b; M2 + M3 → M4 → M5 → M6; M4/M5 → M7a → M7b → M8; M2/M6 → M9a; every slice → M9b. Never call a component before its effects audit/adapter is complete. No fixture bypass substitutes for a production path.

The first runnable increment is M1–M4 focused setup, followed by truthful verification, Risk, assistants and the Spec pathway. This is an incremental implementation order, not a scope reduction. At each milestone run its independent test and update actual completed checkboxes. Keep environment-dependent qualification open when unavailable.

Parallel examples by story: US1 host parser fixtures vs static guidance; US2 Git fixtures vs manifest schema cases; US3 tree fixtures vs catalog card review; US4 advisor fixtures vs isolated Risk fixtures; US5 lock tests vs strict parser vectors; US6 report projection vectors vs connection fixtures; US7 broker auth vectors vs skill copy checks; US8 distinct client intent transcripts; US9 distinct temporary client workspaces; US10 baseline flag snapshots vs saved-plan validation; US11 independent link batches vs local join checks; US12 artifact-class fixtures. Shared production-file edits remain sequential.

## Traceability

Machine-readable complete task-to-FR/SC mapping: [task-coverage.json](task-coverage.json). Analysis validates every FR-001–FR-056, SC-001–SC-014 and all twelve stories against this mapping; broad final qualification tasks supplement, not replace, concrete implementation/test mappings.

Total: **84 tasks**. Story/shared counts: shared: 12, US11: 8, US5: 14, US10: 3, US1: 6, US2: 3, US3: 7, US6: 7, US4: 7, US7: 7, US8: 3, US9: 4, US12: 3.

Mac closure checkpoint (2026-10-18): M01–M08 passed; 81/84 checked. T081 retains Windows/WSL qualification, T082 native Windows, T084 final cross-platform reconciliation. T083 evidence is synthetic and does not claim the later owner walkthrough. See MAC-COMPLETION.md.

WSL return checkpoint (2026-10-24): still **81/84 checked**. Both releases pass the final 140-test setup suite with all opt-ins; real wizard, Risk, client, management and native Windows subcases are recorded in [the return matrix](../../spec153-wsl-return/matrix.json). T081 remains open for incomplete actual WSL scenarios, T082 for unavailable/unrun native Windows cases, and T084 for Mac reconciliation. The owner requested remote delivery/handoff and host stability; no missing case is counted as passed, and no accepted scope was regenerated or reduced.

Release reconciliation (2026-10-24): **82/84 checked**. T084 closes with the existing milestone draft, three additional actual Mac installer passes, final coverage/status in release-verification.md, daily memory and GAIT. The owner then explicitly authorized merge/publication and branch cleanup. T081 and T082 retain their incomplete Windows/WSL subcases; no unrun platform test is relabeled as passed. Operational capability retesting is outside this installer release scope.
