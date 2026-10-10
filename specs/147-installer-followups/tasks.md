# Tasks: Installer and first-use reliability

## Intake and baseline

- [x] T001 Close spec 146 through PR #288 and start spec 147.
- [x] T002 Receive macOS/Hermes and Linux/OpenClaw reports.
- [x] T003 Pull main, verify Nick's PR #287 is merged and integrate it into this branch.
- [x] T004 Classify every supplied issue in reports.md against current code.
- [x] T005 Reproduce Node policy and native registration gaps; run isolated real-runtime transport probes.
- [x] T006 Verify relevant merged fixes (113 focused tests); define scope and design.

## Phase A — Runtime compatibility/bootstrap

- [x] T007 Add shared target-aware Node compatibility rule and boundary fixtures.
- [x] T008 Add version-aware narrow npm lifecycle-script handling and rootless install recovery.
- [x] T009 Ensure runtime-install/executable failure propagation and clear Python/uv guidance.

## Phase B — Component access

- [x] T010 Declare access paths and expected capabilities for all twelve reported components.
- [x] T011 Bind supported native registrations and skill launchers to managed runtimes.
- [x] T012 Verify pyATS/CML and representative utility discovery without bypassing approval controls.
- [x] T013 Preserve operator state and reconcile inventory/registration/documentation surfaces.

## Phase C — First-use readiness

- [x] T014 Add structured readiness stages and bounded discovery with expected-tool checks.
- [x] T015 Check configured local/remote Ollama endpoint/model readiness and document deferred/live checks.
- [x] T016 Add evidence-backed synthetic canary and unavailable-tool negative cases.
- [x] T017 Record transport diagnosis and limits: synthetic transports plus four real catalogs verified on installed OpenClaw; exact historical CML/runtime trace unavailable, no upstream cause assigned.

## Completion

- [x] T018 Run appropriate unit/installer contracts and declaration/reconciliation checks.
- [x] T019 Record real-host/live acceptance boundaries and operator recovery instructions.
- [x] T020 Prepare one patch release proposal after implementation completes.

The six unnamed macOS component failures and exact original CML/runtime diagnostics remain pending evidence. They do not prevent work on the confirmed scoped defects; they are not invented acceptance cases.

Release proposal: 1.6.2. PR/merge completion is recorded in verification.md once CI passes. Original live target acceptance remains a documented external evidence gap.
