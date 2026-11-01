# Tasks: NetConverter AI and virtual migration rehearsal

**Input**: [spec.md](spec.md), [plan.md](plan.md), [research.md](research.md), [data-model.md](data-model.md), [contracts](contracts/)

Tasks are source work unless explicitly labeled live qualification. Checked tasks require recorded evidence. A blocked live task remains unchecked. Initial implementation and controlled verification are recorded below and in verification.md. Live acceptance remains separate.

## Phase 1 — Specification and research

- [x] T001 Record owner scope, upstream provenance, integration decisions and acceptance contracts in `specs/162-netconverterai/{spec,plan,research,data-model,acceptance-scenarios}.md` and `contracts/`.
- [x] T002 Complete cross-artifact analysis and resolve substantive findings in `specs/162-netconverterai/analysis.md` before implementation.

## Phase 2 — Shared private-artifact and transport foundation

- [x] T003 Add boundary tests for private artifacts, exact-request digests, one-use grants and unknown outcomes in `tests/netconverter/test_core.py`.
- [x] T004 Implement bounded descriptor-based capture, frozen snapshots, hash verification and no-clobber publication in `mcp-servers/netconverter-mcp/artifacts.py`.
- [x] T005 Implement connection/request/grant/attempt state and atomic reservation in `mcp-servers/netconverter-mcp/core.py`.
- [x] T006 Implement official SDK clients, fixed Terminal argv/environment, bounded capability discovery and no mutation retries in `mcp-servers/netconverter-mcp/transport.py`.

Checkpoint: tests distinguish source bytes from metadata and prove a single approved request cannot create two submission attempts.

## Phase 3 — US1: optional integration and readiness (P1)

- [x] T007 [US1] Implement the guarded MCP server/status surface with explicit mode and capability reporting in `mcp-servers/netconverter-mcp/server.py`.
- [x] T008 [US1] Add dependency-only isolated installation and guarded-only runtime registration in `scripts/lib/install-steps.sh`, `scripts/lib/plan-steps.sh`, `config/python-components/netconverter.txt`, `config/openclaw.json`, `config/installer-access.json` and reviewed `config/components/effects.json`.
- [x] T009 [US1] Add conditional per-installation settings, skill/server joins and effect/access metadata in `config/components/catalog.json` and `scripts/lib/setup_generated.py`.
- [x] T010 [US1] Add bounded mode selection and validation in `scripts/setup.sh`, `scripts/lib/setup_plan.py`, `extensions/netclaw-vscode/src/views/setup-wizard.ts` and `extensions/netclaw-vscode/src/setup/plan.ts`; reject `nck_live_` literals in non-secret plan fields.
- [x] T011 [US1] Distinguish installed/discovered/authenticated/capable/approved status in `scripts/installer-readiness.py`, existing setup verification/report projections and `ui/netclaw-visual/server.js`.
- [x] T012 [US1] Verify isolated setup, mode cancellation/save, owner preservation, secret references and guarded-only registrations in `tests/netconverter/test_installation.py`, existing setup tests and extension setup tests.

Independent test: configure each mode against controlled peers with no upstream transfer, owner-runtime change or license acceptance.

## Phase 4 — US2: approved conversion and evidence (P1)

- [x] T013 [US2] Implement local prepare and exact-reference submit-approved operations in `mcp-servers/netconverter-mcp/core.py` and `server.py`, including source/target/options qualification and durable unknown state.
- [x] T014 [US2] Implement operator review/single-use approval/status CLI in `scripts/netconverter-settings.py` without a model-facing grant tool.
- [x] T015 [US2] Implement schema-qualified read allowlist, connection-bound jobs, finite polling and verified private downloads in `mcp-servers/netconverter-mcp/transport.py` and `server.py`.
- [x] T016 [US2] Exercise the actual official SDK with controlled stdio/HTTP peers, denial, malformed receipts, exposure preservation, authentication isolation and corruption/fault cases in `tests/netconverter/test_transport.py`.
- [x] T017 [US2] Adapt the supplied bundle into `workspace/skills/netconverter/SKILL.md` and `references/operations.md`, preserve archive provenance and validate the skill; move the original supplied archive out of the repository root into the documented provenance location without loss.

Independent test: synthetic source → exact operator grant → one controlled submission → evidence review → verified local artifacts, including declined/changed/replayed/unknown cases.

## Phase 5 — US3: actual virtual migration targets (P1)

- [x] T018 [US3] Bind a natively reviewed candidate artifact, endpoint identities, testbed fingerprint, route and verification profile into the existing API request/record in `ui/netclaw-visual/terminal-change-policy.js`, `terminal-intent-execution.js`, `src/canvas-chat/TerminalChangeControl.jsx` and `src/canvas-chat/TerminalLane.jsx`.
- [x] T019 [US3] Implement API-issued one-use apply capabilities after real baseline/rollback transition in `ui/netclaw-visual/terminal-intent-execution.js` and a narrowly scoped shared issuer/consumer contract in `scripts/lib/migration_artifacts.py`; no model-issued approval or phase-file-only authorization.
- [x] T020 [US3] Add mutually exclusive artifact input to the existing managed pyATS configuration tool identity in `scripts/pyats-managed.py`, retaining runtime denial semantics, dangerous-command checks, exact endpoint/testbed binding and one-use attempts.
- [x] T021 [US3] Keep full configuration/diffs/upstream logs private and prove canary non-disclosure for artifact application in `scripts/lib/migration_artifacts.py`, `scripts/pyats-managed.py` and `tests/netconverter/test_private_apply.py`.
- [x] T022 [US3] Test prepare-phase refusal, wrong candidate/endpoint/testbed/harness, forged or replayed capability, denied original tool, interruption and restart in `ui/netclaw-visual/test/terminal-change-policy.mjs`, `test/terminal-intent-execution.mjs` and `tests/netconverter/test_private_apply.py`.
- [x] T023 [US3] Implement bounded rehearsal/resource/evidence manifests and ownership reconciliation in `scripts/lib/migration_artifacts.py`; verify uncertain creation and unowned-resource refusal in `tests/netconverter/test_rehearsal.py`.
- [x] T024 [US3] Author actual provision/boot/apply/test/retain orchestration in `workspace/skills/netconverter/references/rehearsal.md`, discovering installed schemas and qualifying exact image/management/bootstrap support; correct only relevant stale CML tool examples and lab-control advice in existing CML/clab/GNS3 skills.
- [x] T025 [US3] Add explicit parse/query coverage to migration-facing Batfish results in `mcp-servers/batfish-mcp/batfish_mcp_server.py` and tests so partial parses or failed differential queries cannot claim equivalence.
- [x] T026 [US3] Verify the skill's execution decisions against controlled tool fixtures, including actual expected create/boot/test calls, unsupported images/FRR conversion, blocked apply and a deliberately failing traffic assertion; record outcomes in `specs/162-netconverterai/verification.md`.

Independent test: controlled provider/SDK rehearsal proves the actual orchestration sequence and gates; real vendor image acceptance is separately T035–T036. Neither a plan nor an FRR peer counts as a tested target firewall.

## Phase 6 — US4: cross-composition and review package (P2)

- [x] T027 [US4] Add a fixed private artifact-producing collection route as optional metadata-only artifact output on the existing `pyats_show_running_config` identity in `scripts/pyats-managed.py` and `scripts/lib/migration_artifacts.py`; test no raw config reaches model results in `tests/netconverter/test_private_apply.py`; mark other inline-only collector adapters unavailable until qualified.
- [x] T028 [P] [US4] Document inventory/collector/assurance/NetConverter/Jev/Batfish/pyATS handoff contracts and privacy boundaries in `workspace/skills/netconverter/references/composition.md`.
- [x] T029 [P] [US4] Define evidence-linked observed/proposed diagrams, test matrices, retained resources, rollback/manual actions and draft ticket/document workflow in `workspace/skills/netconverter/references/evidence.md` and `docs/NETCONVERTER.md`.
- [x] T030 [US4] Exercise a synthetic collection→conversion→rehearsal→Jev-unavailable→local-review-package case with truthful coverage and no external communication in `tests/netconverter/test_composition.py` and `specs/162-netconverterai/verification.md`.

Independent test: the review package preserves all failures, unsupported/unexecuted checks and artifact provenance through a complete controlled workflow.

## Phase 7 — Coherence and qualification

- [x] T031 Update `README.md`, `SOUL.md`, `SOUL-SKILLS.md`, `TOOLS.md`, `.env.example`, `mcp-servers/netconverter-mcp/README.md` and `ui/netclaw-visual/LOCAL-LAB-CHANGE-CONTROL.md` with actual behavior and platform/control limits.
- [x] T032 Regenerate `scripts/lib/catalog.sh`, `ui/netclaw-visual/env-map.js` and catalog payloads using existing generators; reconcile intentional counts in `tests/fixtures/setup/catalog-baseline.json` and inventory documentation.
- [x] T033 Run applicable catalog, installer, guard, managed-pyATS, Batfish, HUD and extension regressions; record exact versions/results and failures in `specs/162-netconverterai/verification.md`.
- [ ] T034 Perform an isolated native installer/approval UI pass and actual upstream licensed-client discovery when its prerequisites are available; record unavailable stages separately in `specs/162-netconverterai/verification.md`.
- [x] T035 Qualify a compatible authorized host/image/bootstrap and exact-file-approved live NetConverter reference conversion; record image/license/capacity/account evidence and any blockers in `specs/162-netconverterai/verification.md`.
- [x] T036 Create a real virtual migration target, load the approved candidate through the protected route and run actual positive/negative behavior checks; compare source twin where feasible and preserve run resources/evidence in `specs/162-netconverterai/verification.md`.

Live tasks T034–T036 remain unchecked if their external prerequisites are absent; they cannot be satisfied by fixture results. Continue independent source work and review iterations.

2026-10-31 update: real Terminal/account discovery, two native exact-file approvals,
two actual conversions and six verified downloads now complete those portions of
T034/T035. Actual local Batfish/MCP analysis adds scoped model evidence, including
a forward route-metric difference. The owner completed a real native plan review
and minimal installation; scoped repairs now prove Claude/NetConverter execution
and native dynamic pyATS discovery. The original partial setup report is retained.
This is historical October 31 status. The November 1 qualification below supersedes
the CML/target prerequisites; fresh native installation and protected behavior
acceptance remain separate. See [three additional loops](live-iterations.md).

2026-11-01 update: T035 is complete for the available IOS-XE round-trip reference.
Actual CML authentication, five-slot licensing, owned IOS-XE 17.18.2 image boot,
isolated management/data links, SSH identity and private target/peer baselines are
verified. The owner explicitly authorized temporary R1/R2 stop/start; first
restoration was verified against real baselines. Failed bootstrap and legacy-SSH
trials are retained. T034 still requires a fresh native installation acceptance
pass after the discovered fixes; its real HUD candidate/Local-Lab review now runs.
T036 completed a first real apply/forwarding trial, which exposed baseline-file
substitution. Its original configuration remains retained; the source now checks
collector receipts and exact captured bytes. The clean protected repeat now passes:
actual target and independent peer both show OSPF FULL, metric-11 reciprocal routes,
5/5 positive and 0/3 negative pings, with management preserved. T034 is the sole
remaining task; the new exact native plan is validated and awaiting human review.

## Phase 8 — Five Ralph implementation review/fix/test iterations

Each round uses the exact prompt in `ralph-iterations.md`, re-reads the current tasks/evidence, fixes supported findings and runs justified checks. The numbered focus is an additional review lens, not a replacement prompt.

- [x] T037 Run Ralph iteration 1 with the submission/privacy/concurrency lens; record findings, edits and checks in `specs/162-netconverterai/ralph-iterations.md`.
- [x] T038 Run Ralph iteration 2 with the installer/SDK/readiness/preservation lens; record findings, edits and checks in `specs/162-netconverterai/ralph-iterations.md`.
- [x] T039 Run Ralph iteration 3 with the virtual-target/apply-control/failure-recovery lens; record findings, edits and checks in `specs/162-netconverterai/ralph-iterations.md`.
- [x] T040 Run Ralph iteration 4 with the skill/cross-composition/coverage/reporting lens; record findings, edits and checks in `specs/162-netconverterai/ralph-iterations.md`.
- [x] T041 Run Ralph iteration 5 with the full requirement/task/evidence reconciliation lens; record findings, edits and checks in `specs/162-netconverterai/ralph-iterations.md`.

## Phase 9 — Honest completion and handoff

- [x] T042 Update appropriate source/extension versions and history at implemented feature completion in `VERSION`, `CHANGELOG.md`, `extensions/netclaw-vscode/package.json` and the repository's actual version metadata; verify current paths/conventions first.
- [x] T043 Draft the evidence-based community/milestone note in `docs/blog/2026-10-30-netconverterai.md`; no publication or external ticket is implied.
- [x] T044 Reconcile all requirements, actual task states, qualification limits and final GAIT/daily memory in `specs/162-netconverterai/verification.md`, `tasks.md` and the session logs. Do not report 100% or all tasks complete while a required live gate remains unchecked.

## Dependencies and parallel opportunities

T001→T002→foundation T003–T006. US1 enables US2. US3 reuses artifacts and the existing change workflow; its authorization extension is a prerequisite for any live candidate apply. US4 can document contracts in parallel (T028/T029) after they are stable, but its integration test follows conversion/rehearsal support. Coherence follows implemented stories; live qualification depends on external prerequisites. Five iterations follow initial implementation and available verification; unavailable live tasks stay visible. Completion follows iteration 5 and final reconciliation.

Parallel examples: US1 isolated UI tests and backend mode tests use separate fixtures; US2 core and transport tests can run independently after shared implementation; US3 controlled lab-provider and authorization tests use isolated state; US4 T028/T029 are separate documentation files. Mutations to shared catalog, request schema, tool signatures or runtime state remain sequential.

## Implementation strategy

Deliver discovery/guard first, then approved submission, then the protected artifact application and actual rehearsal path, then composed reporting. Test observable boundary/failure behavior, not wording. Keep source and live qualification progress separate. Never reduce a failing control to make the demonstration work.
