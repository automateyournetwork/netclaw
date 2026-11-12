# Tasks: GCP Deployment Setup, Guides and Documentation Refresh (R09C)

## Phase 1: Foundation
- [x] T001 Standard Warning single source `scripts/lib/gcp_warning.txt` (FR-015)
- [x] T002 Pure topology/plan builder `scripts/lib/gcp_topology.py`: no default project, owned names, R09B adopted items (FR-005, 006, 013)
- [x] T003 Provisioner `scripts/netclaw-gcp.py`: plan/apply/status/ssh/bootstrap/teardown, prerequisite checks, hash + cost gates, idempotent, ownership-scoped teardown with verification (FR-007..012, 016, 017)

## Phase 2: Install paths (US1, US2, US3)
- [x] T004 [US1,2,3] `scripts/lib/gcp-menu.sh` + `scripts/install.sh` step: warning, acknowledgement, topology menu, plan, confirm, apply, bootstrap (FR-001, 003, 016)
- [x] T005 [US1,2,3] VS Code `src/setup/gcp.ts`, `src/views/gcp.ts`, command `netclaw.deployGcp`, tests (FR-002)
- [x] T006 [US1] Claw Plan / assistant flow: same CLI, documented; assistant skill forbids supplying acknowledgements (FR-004)

## Phase 3: Docs (US4)
- [x] T007 `docs/NETCLAW-IN-GCP.md`
- [x] T008 README, GETTING-STARTED-VSCODE, ASSISTANT-INSTALL, CLAW-PLAN, netclaw-install SKILL refreshed (FR-020, 021)

## Phase 4: Roadmap (US5)
- [x] T009 Roadmap README, R09B marked complete, R09C brief, R10 depends on R09C (FR-023)

## Phase 5: Tests and checks
- [x] T010 `tests/gcp/test_netclaw_gcp.py` (fake gcloud): warning, no default project, prerequisites, gates, idempotency, exact teardown, partial failure, topologies, no operator hardcodes (SC-003, 005, 007, 008)
- [x] T011 `tests/gcp/test_docs_parity.py`: warning verbatim, topology parity across guide/TUI/extension, doc links, roadmap, cost table vs builder (SC-002, 004, 006, 009)
- [x] T012 Repo checks: verify-inventory-counts, build-catalog --check, reconcile-mcp (docs/catalog/portability pass)
- [x] T013 `verification.md` with honest scope

## Phase 6: Open (needs owner)
- [ ] T014 Real GCP run of at least `gcp-border` and teardown (billed; not run without owner go-ahead)
- [ ] T015 Extension/source version bump and release notes (owner approves every release)
