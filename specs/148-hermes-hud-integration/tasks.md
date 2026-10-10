# Tasks: Hermes integration with the NetClaw HUD

**Inputs**: [spec.md](spec.md), [plan.md](plan.md), [research.md](research.md), [data-model.md](data-model.md), [contracts](contracts/), [quickstart.md](quickstart.md).
**Stage**: Implementation available for host acceptance. Checkboxes reflect the evidence in [validation.md](validation.md); partial host/fault/upgrade tasks remain open. Planned filenames consolidated during implementation are mapped there. Tests are required by SC-001–007.

## Phase 1 — Setup and pinned qualification fixtures

- [X] T001 Record pinned Hermes source/install hashes, constructor/route/guard/storage signatures and fixture provenance in `config/hermes-hud-compatibility.json` and `tests/hermes-hud/README.md`; fail unsupported revisions rather than trusting package version. (FR-019)
- [X] T002 Add the private component scaffold and isolated exact dependencies in `mcp-servers/hermes-hud-mcp/`, `config/python-components/hermes-hud.txt`, `ui/netclaw-visual/package.json` and lockfile; explicitly allow bridge source in `.gitignore` while excluding local state, credentials, venvs and caches. (FR-016,019; constitution V,XIII,XV)
- [X] T003 Build controlled model-provider, real harmless MCP canary and synthetic populated runtime-home fixtures in `tests/hermes-hud/fixtures/`; include forbidden-handler counters, secrets/memory sentinels and missing/partial usage records without live device access. (FR-005,006,016,019)

**Checkpoint**: Dependencies are isolated and fixtures can distinguish a real Hermes invocation from a stubbed HUD answer. No live provider request required.

## Phase 2 — Foundation: selection, ownership and durable admission

- [X] T004 [P] Add precedence/custom-home/invalid-descriptor/unselected-access tests in `tests/unit/test_hud_runtime_selection.py`, including fresh shells, different CWDs, spaces, coexistence, home-A/config-A overridden by home-B, cross-language golden-fixture parity and original OpenClaw defaults. (FR-001–003,017)
- [X] T005 Implement equivalent Python/Node descriptor resolution and private installation UUID in `scripts/runtime-selection.{py,mjs}` and the server loader `ui/netclaw-visual/src/hud-server/runtime/selection.js`; reject invalid state before dotenv/runtime I/O and keep secrets out of descriptors. (FR-001–003,008,016)
- [X] T006 Add owner/runtime binding, post-I/O expiry, atomic admission/restart and duplicate-nonce tests in `ui/netclaw-visual/src/hud-server/bindings.test.js` and `tests/hermes-hud/test_ledger.py`. (FR-008,015–017,021)
- [X] T007 Extend `ui/netclaw-visual/src/hud-server/bindings.js` to schema 2 with selected installation, owned conversation/request lookup and idempotent legacy OpenClaw migration/backup; preserve private-file safeguards. (FR-008,009,016,017,021)
- [X] T008 Implement `mcp-servers/hermes-hud-mcp/ledger.py` with private DBs, conversation mappings, durable one-turn admission fencing, retry fingerprints, uncertainty retention and request-scoped invocation records; no silent in-memory fallback. (FR-004,005,008,014,015,022)
- [X] T009 Add the adapter interface, pinned official MCP client and OpenClaw wrapper in `ui/netclaw-visual/src/hud-server/runtime/{index,mcp-client,openclaw,hermes,capabilities}.js`, consistently passing selected runtime environment and refusing fallback. (FR-002,003,010,018)

**Checkpoint**: Scope and durable admission exist before any agent route is enabled. T004 may be authored alongside T002–T003; T005 follows its tests; T007–T008 follow T006. T009 follows T005/T007/T008.

## Phase 3 — US1: launch the selected runtime (P1)

**Independent test**: Launch Hermes from a fresh shell/custom home with no OpenClaw installed; report accurate staged readiness and preserve OpenClaw default behavior.

- [X] T010 [P] [US1] Add launcher/lifecycle/read-only-readiness integration tests in `tests/hermes-hud/test_launch.py`, including occupied ports, stale process records, invalid identity and zero unintended service/provider/tool starts. (FR-001–003,014,016,019)
- [X] T011 [US1] Persist selection after successful install and implement explicit `hud select`, `hud`, `hud status` in `scripts/netclaw` and `scripts/lib/{common,install-steps}.sh`; support clean shells/custom CWDs without changing existing TUI behavior. (FR-001,002,017)
- [X] T012 [US1] Implement dedicated companion lifecycle and private upstream storage injection in `mcp-servers/hermes-hud-mcp/hermes_api.py`; record/verify absolute Hermes interpreter/source launch identities; source-check API/storage seams, no-op memory checkout, loopback/auth/route allowlist, disable profile dispatch and never patch or restart the owner's process. (FR-002,003,016,017)
- [X] T013 [US1] Implement safe bridge status and adapter readiness in `mcp-servers/hermes-hud-mcp/server.py`, `ui/netclaw-visual/src/hud-server/runtime/hermes.js` and `server.js`; distinguish installed/discovered/authenticated/protected/provider-configured/execution-verified stages. (FR-003,010,014)
- [X] T014 [US1] Display selected installation and actionable launch/readiness states in `ui/netclaw-visual/src/dashboard/{Dashboard,WorkspaceTools}.jsx` and support the same resolution through `ui/netclaw-visual/server.js` npm startup. (FR-001–003,014)

**Checkpoint**: Reachable HUD is not labeled verified agent execution. A missing companion has a recovery action; panel reads do not launch it.

## Phase 4 — US2: real Hermes conversation and eligible tools (P1)

**Independent test**: A real pinned Hermes agent completes contextual turns using the controlled provider and registered canary; forbidden tool/memory/provider routes execute nothing. Live-provider acceptance occurs later.

- [X] T015 [P] [US2] Write protected-agent tests in `tests/hermes-hud/test_protected_agent.py` for constructor drift, implicit/plugin tools, changed schemas/config, refresh, optional-hook failure, forged terminal/code/delegate/history calls, shared-memory leakage and alternate agent providers. (FR-004–006,008,016,020)
- [X] T016 [US2] Implement `protected_agent.py` and `policy.py` under `mcp-servers/hermes-hud-mcp/` plus `config/hermes-hud-tool-policy.json`: freeze qualified tool/server identities, guard every inference/dispatch, suppress shared memory/refresh, constrain static/skill reads, and reject unqualified writes before execution. (FR-004–006,008,016,020)
- [X] T017 [US2] Capture companion-owned correlated invocation/result evidence in `mcp-servers/hermes-hud-mcp/{protected_agent,ledger}.py`, preserving request/session/run attribution across compression; sanitize output and never infer proof from prose or numeric transcript intervals alone. (FR-005,008,016)
- [X] T018 [US2] Implement eight MCP tools and bounded upstream run/session calls in `mcp-servers/hermes-hud-mcp/server.py`, including persist-before-POST, server-owned IDs, text/seed limits, deadline and safe structured failures. (FR-004,005,008,014,015,022)
- [X] T019 [US2] Route owned chat/admission/status/progress and synchronous compatibility chat through the common adapter in `ui/netclaw-visual/server.js`; enforce local-origin/auth checks, post-I/O expiry checks and no global/latest-session fallback. (FR-002,004,008,014–016,022)
- [X] T020 [US2] Integrate bounded request/progress display and actual answer attribution in `ui/netclaw-visual/src/dashboard/StandardChat.jsx`; retain drafts on rejected submission and show actual model/provider metadata only when known. (FR-004,005,011,022)
- [X] T021 [US2] Route agent-assisted submission/evidence through the adapter in `ui/netclaw-visual/terminal-intent-{execution,live}.js`, preserving `terminal-change-policy.js`; refuse unsupported Hermes APPLY and wider grants before dispatch while leaving direct terminal presentation intact. (FR-006,018,020)
- [X] T022 [US2] Register and run the real pinned-agent/controlled-provider/real-MCP-tool scenario in `tests/hermes-hud/test_agent_integration.py`; prove context, installed eligible skill use, actual tool evidence, denied bypass and unchanged owner runtime files. (FR-004–006,008,016,019,020)

**Checkpoint**: Protection tests and useful real read-only tool execution both pass. An always-deny bridge or provider-only substitute does not pass.

## Phase 5 — US3: history, Canvas and local Avatar (P1)

**Independent test**: Reopen owned conversations, switch Chat/Avatar without work, continue two branch-point contexts and deny every cross-owner/installation lookup.

- [X] T023 [P] [US3] Add cross-owner/runtime/expired-owner/legacy-route/history-compaction tests in `ui/netclaw-visual/src/hud-server/{bindings,chat-history}.test.js` and browser origin tests in `src/dashboard/chat-storage.test.js` under the same UI root. (FR-007–009,013,016,021)
- [X] T024 [US3] Implement owned list/history/evidence projections in `ui/netclaw-visual/src/hud-server/chat-history.js`, runtime adapters and `server.js` session/tool routes; never accept raw native IDs or disclose output after expiry. (FR-005,008,009,016)
- [X] T025 [US3] Namespace and migrate browser work by installation in `ui/netclaw-visual/src/dashboard/chat-storage.js` and `src/canvas-chat/App.jsx`; retain backups, uncertain-origin work read-only and server ownership for transcript reopen. (FR-007–009,017,021)
- [X] T026 [US3] Implement one-time validated ancestor seeding and independent Canvas session mappings in `ui/netclaw-visual/src/canvas-chat/App.jsx` and `src/hud-server/runtime/hermes.js`; preserve graph content and reject unsupported attachments before admission. (FR-004,007,008,021,022)
- [X] T027 [US3] Preserve shared Chat/local Avatar context and side-effect-free view switching in `ui/netclaw-visual/src/dashboard/{StandardChat,LocalPal,Dashboard}.jsx`, with browser tests in `src/dashboard/{pal-ui,local-pal-audio}.test.js`. (FR-007,008,018)
- [X] T028 [US3] Update classic `ui/netclaw-visual/src/main.js` and `src/hud-server/control-ui.js` to obtain owned bindings, retain compatible supported chat behavior and show only valid runtime-native navigation. (FR-008,013,018,021)

**Checkpoint**: Browser and server isolation agree. Legacy OpenClaw work is preserved without becoming Hermes context automatically.

## Phase 6 — US5: bounded failures and safe recovery (P1)

**Independent test**: Drop admission/status/event connections, restart every process and verify specific errors, deadlines and zero automatic replays; approval/stop remains exact and owned.

- [ ] T029 [P] [US5] Add fault/restart/concurrency/nonce/expiry/approval tests in `tests/hermes-hud/test_recovery.py` and `ui/netclaw-visual/src/hud-server/runtime/recovery.test.js`, including failed ledger writes and every documented error category. (FR-008,014–016,020,022)
- [X] T030 [US5] Implement status-only reconciliation, persistent uncertainty, bounded HTTP/progress and admission fencing in `mcp-servers/hermes-hud-mcp/{server,ledger}.py` and `ui/netclaw-visual/src/hud-server/runtime/hermes.js`; never replay ambiguous POST. (FR-014,015,022)
- [X] T031 [US5] Wire owned exact once/deny approval and cooperative stop through `ui/netclaw-visual/server.js` and `mcp-servers/hermes-hud-mcp/server.py`, rejecting stale/bulk/enduring grants; only observed terminal state establishes cancellation. (FR-006,008,016,022)
- [X] T032 [US5] Implement shared unknown/interrupted/policy/compatibility UI states, explicit uncertain-request acknowledgment when starting a new conversation, and draft-preserving failures in `ui/netclaw-visual/src/dashboard/StandardChat.jsx` and `src/canvas-chat/App.jsx`; remove heuristic successful-answer fallbacks. (FR-004,007,014,015,022)
- [X] T033 [US5] Verify event gaps, late results, transcript compression and actual tool attribution in `tests/hermes-hud/test_evidence.py` and `ui/netclaw-visual/test/terminal-intent-live.mjs`; no unowned/uncorrelated proof or raw reasoning output. (FR-005,008,015,016,020)

**Checkpoint**: An uncertain operation stays uncertain across restart; starting fresh never claims the previous work stopped or rolled back.

## Phase 7 — US6: install, upgrade and OpenClaw compatibility (P1)

**Independent test**: Upgrade seeded Hermes/OpenClaw homes, migrate legacy OpenClaw env/browser/bindings explicitly, and compare preservation hashes; native Windows Hermes refuses without OpenClaw side effects.

- [ ] T034 [P] [US6] Add populated-installation, root `.env`, idempotent migration/rollback and private-registration tests in `tests/unit/test_hermes_hud_installer.py` and `tests/installer/`; include custom homes, existing YAML/skills, no global dependency writes and no silent provider/gateway startup. (FR-001,012,016–019,021)
- [X] T035 [US6] Implement explicit safe legacy OpenClaw credential-source migration using `scripts/import-env.py` and runtime-selection preflight, preserving selected `.env` values; Hermes never implicitly imports repository/OpenClaw secrets. (FR-001,012,016–018)
- [X] T036 [US6] Add `hermes-hud` catalog/profile/install entries, `hud-private` manifest/readiness handling and HUD-specific Node/Python requirements in `scripts/lib/{catalog,install-steps}.sh`, `config/installer-{access,runtime}.json` and `scripts/installer-readiness.py`. (FR-001–003,017,019; constitution XI)
- [X] T037 [US6] Exclude the private conversation server from `scripts/openclaw-to-hermes-mcp.py` and `scripts/register-all-mcps.py`; add explicit external/private coverage in `scripts/verify-{catalog-coverage,inventory-counts}.py` and tests proving no recursive agent registration. (FR-006,016,017,019; constitution V,XI)
- [ ] T038 [US6] Honor selected runtime or refuse unsupported native Windows Hermes before any OpenClaw action in `Start-NetClaw.ps1`, `Start-NetClaw-Canvas.ps1`, `Restart-NetClaw-API.ps1` and relevant launch tests without adding a Python requirement; document WSL Linux launch separately and test supported OpenClaw Node versions. (FR-001,002,017–019)
- [ ] T039 [US6] Update `scripts/upgrade-hud.sh` with compatible selection/component preflight and migration guidance; preserve no-unrequested-restart behavior and owner config/browser backups, verifying seeded upgrade/rollback tests. (FR-012,017,018,021)
- [X] T040 [US6] Add `hermes-hud` to `tests/contract-suites.json` and relevant `.github/workflows/{hud-ci,mcp-reconciliation}.yml` triggers/jobs; distinguish offline/real-agent/live-provider evidence and fail required capability gaps explicitly. (FR-018,019)

**Checkpoint**: No original owner credentials/config/tools/skills/saved work lost; OpenClaw's supported path and stricter existing runtime requirements remain intact.

## Phase 8 — US4: selected-runtime controls and evidence (P2)

**Independent test**: Distinct synthetic runtime values never cross; supported actions work only on the selected installation and unsupported controls reject before writing or dispatch.

- [X] T041 [P] [US4] Add selected-source/redaction/capability/config-writer tests in `ui/netclaw-visual/src/hud-server/{runtime-settings,chat-models,chat-usage,workspace-tools}.test.js` and `src/security/{server-access,budget-policy}.test.js`. (FR-003,010–012,016,018)
- [X] T042 [US4] Implement typed selected-runtime model/usage/config/log/tool/skill projections in `ui/netclaw-visual/src/hud-server/{runtime-settings,chat-models,chat-usage,tokenomics,configuration,logs,jev-reader}.js`; label unknown/stale/derived values and qualify real evidence. (FR-003,005,010,011,016)
- [X] T043 [US4] Route or reject every env/budget/Terra configuration writer in `ui/netclaw-visual/server.js` through allowlisted selected-source operations, preserving unrelated values and refusing unsupported Hermes edits before mutation. (FR-010–012,016,017)
- [X] T044 [US4] Resolve startup known-hosts/aliases/topology grants/local records/layout/RAG/Jev paths through the selected installation in `ui/netclaw-visual/server.js` and affected helpers; add synthetic unselected-I/O regression coverage in `test/topology-api.mjs`. (FR-001,003,008,010,012,016)
- [X] T045 [US4] Render truthful selected-runtime panels/model/effort/native-UI/graph states in `ui/netclaw-visual/src/dashboard/{Dashboard,ReferenceViews,WorkspaceTools}.jsx` and classic `src/main.js`; pure view loads execute no inference/tool calls. (FR-003,010,011,013,018)
- [X] T046 [US4] Reject unavailable Hermes federation/hosted-Pal actions in `ui/netclaw-visual/server.js` and `src/hud-server/pal-runtime.js`, pair UI limitations with backend checks, and preserve existing OpenClaw federation/local Avatar regressions. (FR-007,018)

**Checkpoint**: No unsupported feature masquerades as working; missing usage does not become a verified zero.

## Phase 9 — Coherence, acceptance and handoff

- [X] T047 [P] Write private server transport/tools/privileges/setup/troubleshooting in `mcp-servers/hermes-hud-mcp/README.md` and focused `workspace/skills/hermes-hud-diagnostics/SKILL.md`; document status-only diagnostics without registering recursive conversation tools. (FR-003,014,019; constitution VII,XI,XII)
- [X] T048 Update `README.md`, `SOUL.md`, `TOOLS.md`, `.env.example`, `ui/netclaw-visual/LOCAL-LAB-CHANGE-CONTROL.md` and HUD guidance with architecture, capability limits, migration, exact compatibility and selected-runtime launch; reconcile counts through tooling. (FR-001,005,006,010,017–020; constitution XI–XIII)
- [X] T049 Add private-app integration input to `scripts/build-hud-reference.py`, regenerate applicable `docs/reference/{interfaces,hud-openapi,documents}.json` and verify catalog/inventory/reference coherence with no agent-native bridge registration. (FR-010,018,019; constitution X–XII)
- [X] T050 Create a separately invoked live acceptance harness and redacted report format in `tests/hermes-hud/live_acceptance.py` and `specs/148-hermes-hud-integration/validation.md`, recording commit/runtime/host/provider/policy identity and distinguishing fixtures from live evidence. (FR-004,005,019; SC-001–007)
- [X] T051 Run targeted HUD, security, Terminal Intent, installer, protected-agent, MCP, dependency and generated-reference regressions from `quickstart.md`; record results and fix failures in `specs/148-hermes-hud-integration/validation.md` without weakening assertions. (FR-001–022; SC-001–007)
- [ ] T052 Complete browser acceptance for Chat/local Avatar, Canvas branching, scoped storage/history, progress/approval, draft retention and selected-runtime panels; save sanitized results in `specs/148-hermes-hud-integration/validation.md`. (FR-003–004,007–016,018,021,022; SC-002–006)
- [ ] T053 Complete Mac live five-turn/context/tool/skill and upgrade acceptance with qualified Hermes and existing OpenClaw; record exact environment and evidence in `specs/148-hermes-hud-integration/validation.md`. (FR-001–022; SC-001–007)
- [X] T054 After Mac implementation/testing, assess remaining Linux/WSL cases and, if another machine is needed, write `specs/148-hermes-hud-integration/validation-handoff.md` with exact transferable commit, setup/commands/evidence and closure criteria; otherwise record why no handoff is needed in `validation.md`. (FR-019; user's WSL direction)
- [ ] T055 Complete required Ubuntu/WSL integration, Windows-browser loopback/auth, permission/persistence/restart/canary and OpenClaw preservation checks from the handoff or local environment; append pass/fail/unverified evidence to `specs/148-hermes-hud-integration/validation.md` and resolve failures before closure. (FR-001–022; SC-001–007)
- [ ] T056 Reconcile release metadata (`VERSION`, `CHANGELOG.md` and any actual release-linked manifests identified by `CONTRIBUTING.md`) with repository conventions/current main; target minor 1.7.0 from 1.6.2 only after acceptance, and document user-visible limitations/migration. (FR-018,019)
- [X] T057 Draft the milestone article locally in `specs/148-hermes-hud-integration/blog-draft.md`, with tested evidence and remaining limitations; no publication, PR or external message without the owner's separate direction. (FR-019; constitution XIV,XVII)
- [ ] T058 Re-run artifact/diff checks, reconcile task checkboxes against actual evidence, record final notes in `memory/YYYY-MM-DD.md` and GAIT, and report completed scope or exact remaining validation blockers through `specs/148-hermes-hud-integration/validation.md`. (FR-019; constitution IV,XVI)

## Dependencies and parallel opportunities

```text
Setup T001–T003 → Foundation T004–T009 → US1 T010–T014
 → US2 T015–T022 → US3 T023–T028 → US5 T029–T033
 → US6 T034–T040 → US4 T041–T046 → completion T047–T058
```

Default execution is sequential in this order. Story test-authoring tasks marked `[P]` can run alongside the preceding story after Foundation because they create distinct files or the test files are not concurrently edited; they must finish before their corresponding implementation. T023 shares binding tests with T006, so only parallelize after Foundation completes. T041 touches tests that can share history with earlier work; schedule after US3. Never parallelize modifications to `server.js`, installer steps, shared adapters or Canvas storage. `[P]` permits scheduling, not unattended network operations or extra agents.

Examples per story: T010 launcher tests while completing T009 adapter wiring; T015 protected tests while completing T014 display; T023 isolation tests while T020–T021 UI/Terminal code finishes; T029 recovery tests while T027 Avatar work finishes; T034 upgrade tests while T032 recovery UI finishes; T041 metadata tests while T039 upgrade script work finishes. T047 independent docs may run after API/schema finalization alongside regression execution. Implementation tasks within each shared-file group remain ordered.

## Delivery strategy

US1 is the first demonstrable checkpoint, not sufficient for release. US2–US3 establish real agent value and private workspace behavior. US5 and US6 secure recovery/upgrades before US4 completes operational panels. Every story and the protected-agent/live-platform gates are required for final acceptance. All eight declared MCP tools, selected-runtime writers and legacy routes need coverage. Do not substitute skipped platform tests or unsupported core chat/tools for feature completion; prepare the authorized WSL handoff when needed.

## Remaining task evidence

- T029: deterministic lost POST, restart, late result, persistence and exact approval tests pass; the full host failure-category matrix remains in the handoff.
- T034/T039: populated-home selection, private registration, dotenv preservation and build preflight tests pass; full populated upgrade/rollback/browser preservation acceptance remains open.
- T038: early native-Windows refusal is implemented; actual PowerShell and native OpenClaw regression need the Windows host.
- T052/T053/T055: real browser, owner-provider and cross-platform acceptance remain open.
- T056: release preparation waits for acceptance; VERSION remains 1.6.2.
