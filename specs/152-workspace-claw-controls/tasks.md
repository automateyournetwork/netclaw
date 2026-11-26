# Tasks: Workspace Files and Claw Controls

All five user stories are required. Owner authorized implementation, verification and ephemeral preview, then packaging and feature-branch push with a WSL inspection handoff. The owner subsequently authorized production PR/merge/publication on 2026-10-16. Tests below are required by spec acceptance.

## Phase 1 — Setup and design

- [x] T001 Record owner authorization, runtime/service scope and preview hold in specs/152-workspace-claw-controls/spec.md and USER.md.
- [x] T002 Research workspace, lifecycle ownership and native editor acceptance in specs/152-workspace-claw-controls/research*.md.
- [x] T003 Complete plan, data model, contracts and quickstart in specs/152-workspace-claw-controls/; update AGENTS.md context.
- [x] T004 Analyze requirements/task coverage and resolve findings in specs/152-workspace-claw-controls/analysis.md before implementation.

## Phase 2 — Foundations

- [x] T005 Add isolated runtime/process fixtures and private filesystem/identity fault cases in extensions/netclaw-vscode/test/claw-fixture.mjs and claw-files.test.mjs.
- [x] T006 Implement bounded fixed-operation helper entry, validated target/environment, private locks and operation journals in scripts/claw-control.mjs and scripts/lib/claw-files.mjs. Covers FR-003/008/009/011/013/027/028.
- [x] T007 Add session-authenticated read-only installation discovery in ui/netclaw-visual/server.js and contract tests in extensions/netclaw-vscode/test/claw-discovery.test.mjs. Covers FR-003/027/030/031.
- [x] T008 Add native helper client and persistent offline selection binding in extensions/netclaw-vscode/src/client/claw.ts and src/state/management.ts. Covers FR-003/012/019/022/027/031.

## Phase 3 — US1: Connect and read

- [x] T009 [US1] Implement native OpenClaw agent workspace inspection, Hermes home resolution, catalog and bounded exact reads in scripts/lib/claw-files.mjs. Covers FR-002/003/004/026.
- [x] T010 [US1] Add top Connections entries and management workspace page with inert source presentation in extensions/netclaw-vscode/src/extension.ts and src/views/workspace.ts. Covers FR-001/002/004/013.
- [x] T011 [US1] Verify six-file catalog, wrong target, missing/unreadable/oversized files, no external rendering and stale responses in extensions/netclaw-vscode/test/claw-files.test.mjs and claw-view.test.mjs. Covers SC-001/002/009.

## Phase 4 — US2: Edit and save

- [x] T012 [US2] Implement complete draft/review/verified replacement with private originals, scope/revision checks and unknown outcomes in scripts/lib/claw-files.mjs. Covers FR-005/007/008/009/011/028.
- [x] T013 [US2] Implement in-memory editing, exact newline/BOM handling, diff review, save, recovery and dirty navigation in extensions/netclaw-vscode/src/views/workspace.ts and resources/workspace.js. Covers FR-005/008/009/012/029.
- [x] T014 [US2] Verify every-file round trips, Unicode/CRLF/BOM, conflicts, permissions, link/inode swaps, injected failure and private evidence in extensions/netclaw-vscode/test/claw-files.test.mjs and claw-view.test.mjs. Covers SC-002/003/009.

## Phase 5 — US4: Full lifecycle

- [x] T015 [US4] Implement durable owned process observation, graceful stop and managed HUD launch in scripts/lib/claw-process.mjs and scripts/hud-launch.mjs. Covers FR-014–020/022.
- [x] T016 [US4] Implement exact validated native gateway/federation supervisor control and ownership-bound foreground fallback in scripts/lib/claw-services.mjs. Covers FR-014–020/027.
- [x] T017 [US4] Implement lifecycle prepare/apply, dependencies, interruption disclosure, durable phase journals and reconciliation in scripts/claw-control.mjs. Covers FR-014–022/028.
- [x] T018 [US4] Add Start/Stop/Restart, progress, offline status/Start and same-identity reconnection in extensions/netclaw-vscode/src/views/workspace.ts, src/state/management.ts and src/extension.ts. Covers FR-001/014/017/020/021/022.
- [x] T019 [US4] Verify actual owned fixture stop/start/restart for both runtimes, neighboring-installation isolation, supervised stop, stale records, lost response and recovery in extensions/netclaw-vscode/test/claw-lifecycle.test.mjs. Covers SC-004/006.

## Phase 6 — US3: Upload/overwrite

- [x] T020 [US3] Add native file selection, strict UTF-8/size validation, explicit destination replacement and missing-file creation in extensions/netclaw-vscode/src/views/workspace.ts and scripts/lib/claw-files.mjs. Covers FR-006/007/010/011.
- [x] T021 [US3] Verify every target, exact bytes, empty replacement, cancelled upload, invalid input, no-delete dispatch and missing-to-existing race in extensions/netclaw-vscode/test/claw-files.test.mjs and claw-view.test.mjs. Covers SC-002/003/009.

## Phase 7 — US5: Save and restart

- [x] T022 [US5] Add combined exact-content/service review, verified-save prerequisite and separate phase results in extensions/netclaw-vscode/src/views/workspace.ts and resources/workspace.js. Covers FR-023/024/025/026.
- [x] T023 [US5] Verify zero restarts after Save alone/cancel/conflict/failure/unknown, one restart after verified save, and changed-scope refusal in extensions/netclaw-vscode/test/claw-workflow.test.mjs. Covers SC-005/006.

## Phase 8 — Acceptance and owner preview

- [x] T024 Verify bindings survive editor restart, no unsafe assistant grants, older runtime handling and permissions/policy refusal in extensions/netclaw-vscode/test/claw-lifecycle.test.mjs and claw-view.test.mjs. Covers FR-027/028/030/031.
- [x] T025 Add native editor acceptance and isolated two-runtime preview launcher in extensions/netclaw-vscode/test/editor-workspace.cjs and scripts/workspace-preview.mjs. Covers SC-001–009.
- [x] T026 Run typecheck/build, focused tests and affected extension/HUD/helper regressions; resolve findings and record results in specs/152-workspace-claw-controls/verification.md.
- [x] T027 Run actual editor typing, upload/review/save, combined restart, Stop→Start, three themes, narrow/zoom and screenshot review; fix defects and record evidence in specs/152-workspace-claw-controls/verification.md.
- [ ] T028 Measure read/save latency and lifecycle feedback; inspect logs/journals for private-content leaks in extensions/netclaw-vscode/test/claw-lifecycle.test.mjs and specs/152-workspace-claw-controls/verification.md. Covers SC-008/009.
- [x] T029 Update extensions/netclaw-vscode/README.md, PRIVACY.md, CHANGELOG.md and root README.md/SOUL.md/TOOLS.md; verify catalog coherence and preserve release hold.
- [x] T030 Record completed tasks, residual qualification limits and local milestone draft in specs/152-workspace-claw-controls/{tasks,verification,milestone-draft}.md; update daily memory and GAIT.
- [x] T031 Launch the verified source build in a fresh ephemeral VS Code, leave it visible with both isolated connections, and record exact preview/build metadata in specs/152-workspace-claw-controls/verification.md. The owner subsequently authorized package/push for WSL inspection; live deployment remains held.

Follow-up (2026-11-25), outside the original 31 tasks:

- [x] T032 Cache the native `openclaw agents list --json` result behind GET `/api/hud/management` in ui/netclaw-visual/src/hud-server/management.js. Key it on the CLI file, launch CWD/HOME, OpenClaw home, state directory, profile, config path and config-file signature; expire entries after 10 minutes; share concurrent runs; keep no failures; keep only `id`, `isDefault` and `workspace`. Tests in ui/netclaw-visual/src/hud-server/management.test.js; evidence in specs/152-workspace-claw-controls/verification.md.

## Dependencies and independent acceptance

Foundations precede US1. US2 and US4 build on the shared binding; US3 uses US2's write transaction; US5 requires US2/US3 and US4. Each story has its own tests before integrated editor acceptance. US1 reading can be validated without writes; US2 editing without lifecycle; US3 imports without lifecycle; US4 lifecycle without editing; US5 links verified phases.

Independent file-test, service-test and documentation checks can run concurrently after their shared prerequisites. Production code edits are sequenced to avoid shared-file conflicts. Every story and the preview are required; no MVP-only handoff satisfies this task.

## Closure notes

T028 fixture read/save measurements and privacy checks are complete; sub-second renderer progress timing remains uninstrumented and real CLI latency exceeded two seconds cold. See verification.md. All implementation tasks and the Mac native preview are complete within the recorded qualification scope; this is not a claim of live WSL acceptance or every layout/keyboard matrix permutation. The owner explicitly requested the package/push handoff to continue real-host inspection there.
