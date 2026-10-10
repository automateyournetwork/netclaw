# Implementation validation and handoff

The commands below now exist. This procedure is not itself test evidence: see [validation.md](validation.md) for actual Mac results and [validation-handoff.md](validation-handoff.md) for remaining host acceptance. Use synthetic private homes and harmless tool fixtures; never overwrite an owner's installation or run production device writes to test this integration.

## Prerequisites and evidence

Use branch `148-hermes-hud-integration`; record exact implementation commit, OS/architecture, Node/Python versions, Hermes v0.21.6 revision/install provenance, tested model/provider, tool-policy digest and fixture hashes. Keep keys in ignored private `.env`; redact reports. Bridge Python is isolated from Hermes' interpreter and from global packages. Preserve baseline hashes and copies of seeded owner config/skills/browser work.

| Environment | Required evidence | Current status |
|---|---|---|
| macOS 26.5.2 arm64 | Deterministic suites, real protected Hermes fixture, browser flows, live five-turn/provider/tool test | Automated + real fixture passed; browser/live-provider open |
| Ubuntu 24.04 x86_64 | Same core integration/launch/preservation and browser checks | Not run |
| Windows 11 WSL2 / Ubuntu 24.04 x86_64 | Linux paths, private file modes, clean-shell launch, Windows-browser loopback/authentication, persistence/restart and live canary | Not run |
| Native Windows + Hermes | Early unsupported-host refusal, zero OpenClaw startup/config mutation | Source/resolver coverage; actual host open; Hermes support excluded |
| Existing OpenClaw | Current CI and supported-launch regression, owned history/migration, model controls, Canvas/local Avatar, Terminal Intent and panels | Automated regressions passed; owner walkthrough open |

Do not claim every listed platform is supported until its required evidence passes. WSL is a Linux runtime target, not support for the native Windows PowerShell Hermes launch path.

## Deterministic checks after code is built

From repository root:

```sh
python3 scripts/run-contract-tests.py --suite hermes-hud --prepare --strict-capabilities
bash tests/installer/run-tests.sh
python3 scripts/verify-catalog-coverage.py
python3 scripts/verify-inventory-counts.py
python3 scripts/check-fastmcp-compat.py
python3 scripts/verify-spec-artifacts.py
```

From `ui/netclaw-visual/`:

```sh
npm ci
npm test
npm run test:bundle
npm run test:canvas
npm run test:intent-execution
npm run test:intent-live
npm run test:intent-live-ui
npm run test:change-policy
npm run test:topology-api
```

Run `python3 tests/hermes-hud/run_real_fixture.py` separately for the required real pinned Hermes/controlled provider/real canary MCP process tests. Pure HTTP stubs are insufficient for proving protected-agent guards. Tests never require a paid provider by default; live provider checks are a separate explicit invocation with the operator's configured provider and safe canary. CI must report a missing capability rather than silently skip a required gate. Preserve existing assertions and include generated-reference verification through the repository's existing build/check workflow.

## Acceptance sequence

1. **Selection and launch (US1; FR-001–003,019):** Select Hermes into a temporary custom home containing spaces through `scripts/netclaw hud select --runtime hermes --home <absolute-home>`. Start from a new shell and unrelated CWD using the absolute launcher path. Remove OpenClaw from fixture PATH and instrument unselected-home accesses. `hud status` stays read-only. Launch explicitly; verify installation ID, safe status and authenticated loopback companion. Repeat with both runtimes, an explicit override, invalid descriptor/kind and unavailable selected home. Zero silent fallback or unselected credential/state access.
2. **Real agent/tools/skills (US2; FR-004–006,016,020,022):** Complete five contextual text turns through Hermes; use a known read-only registered MCP canary and an eligible installed skill. Match actual result/invocation IDs to owned transcript boundaries. Prove forbidden shell/code/delegate/history/memory/plugin/dynamic-tool/alternate-provider routes cannot execute. Exercise missing and denied tools, unexpected schemas and guard failures. Unsupported write/APPLY refuses before dispatch even after a broad approval attempt. Preserve OpenClaw's existing authorization test suite.
3. **Views and ownership (US3; FR-007–009,013,016,021–022):** Switch Chat/local Avatar without submission; create two Canvas branches at different turn points and verify each intended ancestor context only. Refresh/reopen owned history. Attempt cross-owner, cross-installation, stale cookie, expiry during I/O, raw upstream ID and global legacy-route access; observe no disclosure or upstream call for invalid scope. Inspect browser storage and verify old OpenClaw work remains preserved and is never sent to Hermes. Unsupported attachments preserve the draft.
4. **Failure and control (US5; FR-014–015,020,022):** Missing config/stopped runtime/rejected auth/unsupported revision/provider error produce specific recovery instructions. Drop admission response, disconnect SSE, lose status, stop/deny, restart bridge/companion/HUD and expire owners mid-run. Verify bounded deadlines, exact once/deny approvals, truthful stopping state, durable unknown outcomes and zero replay. Retry identical browser nonce and submit concurrent turns; ensure one admission per conversation. Verify event gaps do not invent evidence.
5. **Panels and mutations (US4; FR-010–012,018):** Seed distinct runtime settings/logs/usage/tools; Hermes displays only its own sources and missing metrics remain unavailable. Exact model/effort controls are disabled when unqualified; actual runtime metadata remains visible. Exercise supported allowlisted edit preservation and unsupported env/budget/Terra settings before-write refusal. Probe federation/hosted-Pal actions server-side. Loading any panel must invoke zero inference or operational tools.
6. **Upgrade and OpenClaw regression (US6; FR-001,012,017–021):** Upgrade populated isolated homes; compare configuration, credential, registration, skill, transcript and browser workspace fixtures to baseline. Repeat migration/upgrade and rollback. Run current OpenClaw Chat/Canvas/Avatar/model/Terminal Intent/panel flows. Native Windows Hermes selection must refuse before OpenClaw process/config access. No broad installer restart or replacement of owner gateway.

All SC-001–007 require recorded results. Actual provider/tool results must be distinguishable from deterministic fixtures. A missing live environment remains unverified; do not check off its acceptance task based on source inspection.

## Conditional Windows/WSL handoff after implementation

The owner has offered to switch machines after Mac implementation if needed. At that point, assess which Linux/WSL cases remain unrun. If they cannot be completed on the Mac, write `specs/148-hermes-hud-integration/validation-handoff.md` containing:

- Exact branch/commit and clean transfer instructions that exclude `.env`, credentials and personal transcripts; never assume another machine has uncommitted work.
- Windows/WSL/Ubuntu, Node, bridge Python and Hermes revision prerequisites; use the WSL filesystem for private runtime state, not a Windows-mounted directory with incompatible permission semantics.
- Exact commands now known to exist, fixture/isolated-home preparation, provider setup without printing secrets, HUD launch, Windows-browser URL and teardown limited to test-owned processes.
- Remaining cases from the matrix with expected output, report locations and failure triage. Explicitly test loopback forwarding/authentication, permissions, custom paths, persistence, restart/no replay and the real read-only canary.
- Pass/fail/unverified table and evidence needed to close the spec; no feature closure while a required qualification remains open. After validation, return to Mac for the next spec as requested.

Do not ask the owner to switch during planning. If all required Linux/WSL evidence can be obtained here after implementation, report that no handoff is needed.
